from pydantic import BaseModel, Field
from typing import Optional

class CheckIn(BaseModel):
    name: Optional[str] = Field(default="", max_length=100)
    tags: Optional[str] = Field(default="")
    desc: Optional[str] = Field(default="")
    timeout: Optional[int] = Field(default=86400, ge=60, le=31536000)
    grace: Optional[int] = Field(default=3600, ge=60, le=31536000)
    schedule: Optional[str] = None
    tz: Optional[str] = Field(default="UTC")
    manual_resume: Optional[bool] = Field(default=False)
    methods: Optional[str] = Field(default="")
    channels: Optional[str] = None
    unique: Optional[list] = None
    start_kw: Optional[str] = Field(default="")
    success_kw: Optional[str] = Field(default="")
    failure_kw: Optional[str] = Field(default="")
    filter_subject: Optional[bool] = Field(default=False)
    filter_body: Optional[bool] = Field(default=False)

class CheckUpdate(BaseModel):
    name: Optional[str] = None
    tags: Optional[str] = None
    desc: Optional[str] = None
    timeout: Optional[int] = Field(default=None, ge=60, le=31536000)
    grace: Optional[int] = Field(default=None, ge=60, le=31536000)
    schedule: Optional[str] = None
    tz: Optional[str] = None
    manual_resume: Optional[bool] = None
    methods: Optional[str] = None
    channels: Optional[str] = None
    start_kw: Optional[str] = None
    success_kw: Optional[str] = None
    failure_kw: Optional[str] = None
    filter_subject: Optional[bool] = None
    filter_body: Optional[bool] = None
