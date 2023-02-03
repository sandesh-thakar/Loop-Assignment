import uuid
from datetime import datetime, timedelta
from typing import List, Tuple

import boto3
import pandas as pd
import pytz
from fastapi import APIRouter, BackgroundTasks, Depends
from sqlalchemy.orm import Session

from .db import get_db
from .models import Report, StoreHours, StoreStatus, StoreTimeZone

router = APIRouter()


def upload_to_s3(df, file_name):
    s3 = boto3.client(
        "s3",
        aws_access_key_id="AKIAR23YDHGHF7I3IZGQ",
        aws_secret_access_key="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",
        region_name="ap-south-1",
    )
    s3.put_object(Bucket="loopreports", Key=file_name, Body=df.to_csv(index=False).encode())

    return f"https://loopreports.s3.ap-south-1.amazonaws.com/{file_name}"


def get_uptime_and_downtime(
    store_hours_list: List[Tuple[datetime, datetime]], store_status_intervals: List[Tuple[datetime, datetime, str]]
) -> Tuple[int, int]:
    overlaps = []

    i = j = 0

    while i < len(store_hours_list) and j < len(store_status_intervals):
        start1 = store_hours_list[i][0]
        end1 = store_hours_list[i][1]

        start2 = store_status_intervals[j][0]
        end2 = store_status_intervals[j][1]

        max_start = max(start1, start2)
        min_end = min(end1, end2)
        if max_start < min_end:
            overlaps.append((max_start, min_end, store_status_intervals[j][2]))
        if end1 < end2:
            i += 1
        else:
            j += 1

    uptime = downtime = 0

    for interval in overlaps:
        delta = interval[1] - interval[0]
        hours = delta.total_seconds() / 3600

        if interval[2] == "active":
            uptime += hours
        else:
            downtime += hours

    uptime, downtime = round(uptime), round(downtime)

    return uptime, downtime


def get_store_hours_intervals():
    pass


def process_store_data(store_id: str, db: Session) -> Tuple[str, int, int, int, int, int, int]:
    UTC_TIMEZONE = pytz.timezone("UTC")
    DEFAULT_TIMEZONE = "America/Chicago"

    current_time = datetime(2023, 1, 25, 18, 0, 0, tzinfo=UTC_TIMEZONE)  # Assumed a static current time for the demo
    last_hour = current_time - timedelta(hours=1)
    last_day = current_time - timedelta(days=1)
    last_week = current_time - timedelta(days=7)

    # Get the timezone of store
    store_timezone = db.query(StoreTimeZone).filter(StoreTimeZone.store_id == store_id).first()

    if not store_timezone:  # If timezone is not found set it to default timezone
        store_timezone = DEFAULT_TIMEZONE
    else:
        store_timezone = store_timezone.timezone_str

    store_timezone = pytz.timezone(store_timezone)

    # Compute timestamps for current time, last hour, last day and last week for the store timezone
    current_time_of_store_time_zone = current_time.astimezone(store_timezone)
    last_hour_of_store_time_zone = last_hour.astimezone(store_timezone)
    last_day_of_store_time_zone = last_day.astimezone(store_timezone)
    last_week_of_store_time_zone = last_week.astimezone(store_timezone)

    # Get the current day of the week
    current_day = current_time_of_store_time_zone.weekday()

    # Create a dictionary to store all the days for the last week

    # Example - current day is wednesay 25
    # week_datetimes[2] will be datetime object with date 25

    week_datetimes = {}

    for i in range(7):
        day_datetime = current_time_of_store_time_zone - timedelta(days=(current_day - i + 7) % 7)
        day = day_datetime.weekday()

        # Add the datetime to the dictionary
        week_datetimes[day] = day_datetime

    # Get the store hours for the store
    store_hours = db.query(StoreHours).filter(StoreHours.store_id == store_id).all()

    # Create a list for the store hours for a store
    store_hours_list = []

    # Store (start_time, end_time) intervals for each day in the last week in the list
    # as datetime object with timezone of the store

    # If store hours are not found assume it to be open 24 * 7
    if not store_hours:
        for day in range(7):
            start_time = (
                week_datetimes[day].replace(hour=0, minute=0, second=0, microsecond=0).astimezone(UTC_TIMEZONE)
            )
            end_time = (
                week_datetimes[day].replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(days=1)
            ).astimezone(UTC_TIMEZONE)
            store_hours_list.append((start_time, end_time))
    else:
        for item in store_hours:
            day = item.day
            start_time = item.start_time_local
            start_time = (
                week_datetimes[day]
                .replace(hour=start_time.hour, minute=start_time.minute, second=start_time.second, microsecond=0)
                .astimezone(UTC_TIMEZONE)
            )
            end_time = item.end_time_local
            end_time = (
                week_datetimes[day]
                .replace(hour=end_time.hour, minute=end_time.minute, second=end_time.second, microsecond=0)
                .astimezone(UTC_TIMEZONE)
            )

            store_hours_list.append((start_time, end_time))

    # Sort store hours in ascending order
    store_hours_list.sort(key=lambda x: x[0])

    # Compute the uptime and downtime for the last hour
    # Get status datapoints for the last hour
    store_status_in_last_hour = (
        db.query(StoreStatus)
        .filter(
            StoreStatus.store_id == store_id,
            StoreStatus.timestamp_utc.between(
                last_hour_of_store_time_zone.astimezone(UTC_TIMEZONE).replace(minute=0, second=0, microsecond=0),
                current_time_of_store_time_zone.astimezone(UTC_TIMEZONE).replace(minute=0, second=0, microsecond=0)
                + timedelta(hours=1),
            ),
        )
        .order_by(StoreStatus.timestamp_utc)
        .all()
    )

    # Make intervals by extrapolating the observed datapoints

    # Example if 25 Jan 17:10 was active and the next inactive observation was at 25 Jan 20:02 then
    # 25 Jan 17:10 to 25 Jan 20:02 will be considered as an active time interval

    store_status_intervals = []

    for i in range(1, len(store_status_in_last_hour)):
        store_status_intervals.append(
            (
                max(last_hour, store_status_in_last_hour[i - 1].timestamp_utc.replace(tzinfo=UTC_TIMEZONE)),
                min(current_time, store_status_in_last_hour[i].timestamp_utc.replace(tzinfo=UTC_TIMEZONE)),
                store_status_in_last_hour[i - 1].status,
            )
        )

    uptime_last_hour, downtime_last_hour = get_uptime_and_downtime(store_hours_list, store_status_intervals)

    # Compute the uptime and downtime for the last day
    # Get status datapoints for the last day
    store_status_in_last_day = (
        db.query(StoreStatus)
        .filter(
            StoreStatus.store_id == store_id,
            StoreStatus.timestamp_utc.between(
                last_day_of_store_time_zone.astimezone(UTC_TIMEZONE).replace(minute=0, second=0, microsecond=0),
                current_time_of_store_time_zone.astimezone(UTC_TIMEZONE).replace(minute=0, second=0, microsecond=0)
                + timedelta(hours=1),
            ),
        )
        .order_by(StoreStatus.timestamp_utc)
        .all()
    )

    store_status_intervals = []
    i = 1
    start_idx = 0

    if len(store_status_in_last_day):
        curr_status = store_status_in_last_day[0].status

    while i < len(store_status_in_last_day):
        if i == len(store_status_in_last_day) - 1 or store_status_in_last_day[i].status != curr_status:
            store_status_intervals.append(
                (
                    max(last_day, store_status_in_last_day[start_idx].timestamp_utc.replace(tzinfo=UTC_TIMEZONE)),
                    min(current_time, store_status_in_last_day[i].timestamp_utc.replace(tzinfo=UTC_TIMEZONE)),
                    curr_status,
                )
            )

            start_idx = i
            curr_status = store_status_in_last_day[i].status
        
        i += 1

    # for i in range(1, len(store_status_in_last_day)):
    #     store_status_intervals.append(
    #         (
    #             max(last_day, store_status_in_last_day[i - 1].timestamp_utc.replace(tzinfo=UTC_TIMEZONE)),
    #             min(current_time, store_status_in_last_day[i].timestamp_utc.replace(tzinfo=UTC_TIMEZONE)),
    #             store_status_in_last_day[i - 1].status,
    #         )
    #     )

    uptime_last_day, downtime_last_day = get_uptime_and_downtime(store_hours_list, store_status_intervals)

    # Compute the uptime and downtime for the last week
    # Get status datapoints for the last week
    store_status_in_last_week = (
        db.query(StoreStatus)
        .filter(
            StoreStatus.store_id == store_id,
            StoreStatus.timestamp_utc.between(
                last_week_of_store_time_zone.astimezone(UTC_TIMEZONE).replace(minute=0, second=0, microsecond=0),
                current_time_of_store_time_zone.astimezone(UTC_TIMEZONE).replace(minute=0, second=0, microsecond=0)
                + timedelta(hours=1),
            ),
        )
        .order_by(StoreStatus.timestamp_utc)
        .all()
    )

    store_status_intervals = []
    i = 1
    start_idx = 0

    if len(store_status_in_last_week):
        curr_status = store_status_in_last_week[0].status

    while i < len(store_status_in_last_week):
        if i == len(store_status_in_last_week) - 1 or store_status_in_last_week[i].status != curr_status:
            store_status_intervals.append(
                (
                    max(last_week, store_status_in_last_week[start_idx].timestamp_utc.replace(tzinfo=UTC_TIMEZONE)),
                    min(current_time, store_status_in_last_week[i].timestamp_utc.replace(tzinfo=UTC_TIMEZONE)),
                    curr_status,
                )
            )

            start_idx = i
            curr_status = store_status_in_last_week[i].status
        
        i += 1

    # for i in range(1, len(store_status_in_last_week)):
    #     store_status_intervals.append(
    #         (
    #             max(last_week, store_status_in_last_week[i - 1].timestamp_utc.replace(tzinfo=UTC_TIMEZONE)),
    #             min(current_time, store_status_in_last_week[i].timestamp_utc.replace(tzinfo=UTC_TIMEZONE)),
    #             store_status_in_last_week[i - 1].status,
    #         )
    #     )

    uptime_last_week, downtime_last_week = get_uptime_and_downtime(store_hours_list, store_status_intervals)

    return [
        store_id,
        uptime_last_hour,
        uptime_last_day,
        uptime_last_week,
        downtime_last_hour,
        downtime_last_day,
        downtime_last_week,
    ]


def generate_report(report: Report, db: Session) -> None:
    # try:
    # Create a list to store all unique store ids
    import time

    start_time = time.time()

    store_ids = [item.store_id for item in db.query(StoreStatus).distinct(StoreStatus.store_id).all()]

    print(len(store_ids))

    store_ids = store_ids[0:250]

    # List of lists to store data of all stores
    #report_list = [process_store_data(store_id, db) for store_id in store_ids]

    report_list = []
    for i in range(len(store_ids)):
        print(i, store_ids[i])
        report_list.append(process_store_data(store_ids[i], db))


    end_time = time.time()

    print((end_time - start_time) / 60)

    report_df_columns = [
        "store_id",
        "uptime_last_hour",
        "uptime_last_day",
        "uptime_last_week",
        "downtime_last_hour",
        "downtime_last_day",
        "downtime_last_week",
    ]
    report_df = pd.DataFrame(report_list, columns=report_df_columns)

    report_filename = report.report_id + ".csv"

    report_url = upload_to_s3(report_df, report_filename)

    report.status = "Complete"
    report.report = report_url
    db.commit()

    # Set status to failed is any error occurs during report generation
    # except Exception as ex:
    #     print(repr(ex))
    #     report.status = "Failed"
    #     db.commit()

    return


@router.get("/trigger_report")
async def trigger_report(background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    report_id = str(uuid.uuid4())
    report = Report(report_id=report_id, status="Running", report=None)
    db.add(report)
    db.commit()

    background_tasks.add_task(generate_report, report=report, db=db)

    return {"report_id": report_id}


@router.get("/get_report")
async def get_report(report_id: str, db: Session = Depends(get_db)):
    report = db.query(Report).filter(Report.report_id == report_id).first()

    return {"report_id": report.report_id, "status": report.status, "report": report.report}
