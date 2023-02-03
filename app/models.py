from sqlalchemy import BIGINT, Column, DateTime, Index, Integer, String, Time

from .db import Base


class StoreStatus(Base):
    __tablename__ = "store_status"

    store_status_id = Column(BIGINT, primary_key=True, autoincrement=True)
    store_id = Column(String, index=True)
    timestamp_utc = Column(DateTime)
    status = Column(String)


class StoreHours(Base):
    __tablename__ = "store_hours"

    store_hours_id = Column(BIGINT, primary_key=True, autoincrement=True)
    store_id = Column(String, index=True)
    day = Column(Integer)
    start_time_local = Column(Time)
    end_time_local = Column(Time)

    __table_args__ = (Index("store_hours_idx", "store_id", "day"),)


class StoreTimeZone(Base):
    __tablename__ = "store_time_zone"

    store_id = Column(String, primary_key=True)
    timezone_str = Column(String)


class Report(Base):
    __tablename__ = "report"

    report_id = Column(String, primary_key=True)
    status = Column(String)
    report = Column(String)
