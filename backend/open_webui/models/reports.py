import time
import uuid
import logging
from typing import Optional, List
from pydantic import BaseModel
from open_webui.internal.db import Base, get_db, JSONField
from sqlalchemy import Column, String, Text, BigInteger, Boolean

log = logging.getLogger(__name__)

####################
# Report DB Schema
####################

class ReportFeedback(Base):
    __tablename__ = "report_feedback"

    id = Column(String, primary_key=True)
    user_id = Column(String, nullable=True)  # 可以为空支持匿名举报
    message_id = Column(String, nullable=True)  # 相关消息ID
    chat_id = Column(String, nullable=True)  # 相关对话ID
    
    category = Column(String, nullable=False)  # 举报分类
    title = Column(String, nullable=False)  # 举报标题
    description = Column(Text, nullable=True)  # 详细描述
    
    contact_info = Column(String, nullable=True)  # 联系方式(可选)
    screenshot_paths = Column(JSONField, nullable=True)  # 截图路径列表
    
    status = Column(String, default='pending')  # pending, processing, resolved, rejected
    admin_notes = Column(Text, nullable=True)  # 管理员备注
    
    ip_address = Column(String, nullable=True)  # 用户IP
    user_agent = Column(String, nullable=True)  # 用户代理
    
    created_at = Column(BigInteger)
    updated_at = Column(BigInteger)
    resolved_at = Column(BigInteger, nullable=True)

####################
# Pydantic Models
####################

class ReportFeedbackModel(BaseModel):
    id: str
    user_id: Optional[str] = None
    message_id: Optional[str] = None
    chat_id: Optional[str] = None
    
    category: str
    title: str
    description: Optional[str] = None
    
    contact_info: Optional[str] = None
    screenshot_paths: Optional[List[str]] = None
    
    status: str = 'pending'
    admin_notes: Optional[str] = None
    
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    
    created_at: int
    updated_at: int
    resolved_at: Optional[int] = None

class CreateReportForm(BaseModel):
    category: str  # 'inappropriate', 'technical', 'copyright', 'other'
    title: str
    description: Optional[str] = None
    message_id: Optional[str] = None
    chat_id: Optional[str] = None
    contact_info: Optional[str] = None
    screenshot_files: Optional[List[str]] = None  # 文件名列表

class UpdateReportForm(BaseModel):
    status: str
    admin_notes: Optional[str] = None

class ReportListResponse(BaseModel):
    reports: List[ReportFeedbackModel]
    total: int

####################
# Report Table Operations
####################

class ReportFeedbackTable:
    def create_report(
        self, 
        form_data: CreateReportForm,
        user_id: Optional[str] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None
    ) -> Optional[ReportFeedbackModel]:
        try:
            with get_db() as db:
                report = ReportFeedbackModel(
                    id=str(uuid.uuid4()),
                    user_id=user_id,
                    message_id=form_data.message_id,
                    chat_id=form_data.chat_id,
                    category=form_data.category,
                    title=form_data.title,
                    description=form_data.description,
                    contact_info=form_data.contact_info,
                    screenshot_paths=form_data.screenshot_files,
                    ip_address=ip_address,
                    user_agent=user_agent,
                    created_at=int(time.time()),
                    updated_at=int(time.time())
                )
                
                result = ReportFeedback(**report.model_dump())
                db.add(result)
                db.commit()
                db.refresh(result)
                
                return report
        except Exception as e:
            log.error(f"创建举报记录失败: {e}")
            return None
    
    def get_report_by_id(self, report_id: str) -> Optional[ReportFeedbackModel]:
        try:
            with get_db() as db:
                report = db.query(ReportFeedback).filter_by(id=report_id).first()
                return ReportFeedbackModel.model_validate(report) if report else None
        except Exception:
            return None
    
    def get_reports_by_user(self, user_id: str, limit: int = 50) -> List[ReportFeedbackModel]:
        try:
            with get_db() as db:
                reports = db.query(ReportFeedback).filter_by(user_id=user_id).order_by(
                    ReportFeedback.created_at.desc()
                ).limit(limit).all()
                return [ReportFeedbackModel.model_validate(report) for report in reports]
        except Exception:
            return []
    
    def get_all_reports(
        self, 
        status: Optional[str] = None,
        skip: int = 0, 
        limit: int = 50
    ) -> ReportListResponse:
        try:
            with get_db() as db:
                query = db.query(ReportFeedback)
                
                if status:
                    query = query.filter(ReportFeedback.status == status)
                
                total = query.count()
                reports = query.order_by(
                    ReportFeedback.created_at.desc()
                ).offset(skip).limit(limit).all()
                
                return ReportListResponse(
                    reports=[ReportFeedbackModel.model_validate(report) for report in reports],
                    total=total
                )
        except Exception as e:
            log.error(f"获取举报列表失败: {e}")
            return ReportListResponse(reports=[], total=0)
    
    def update_report_status(
        self, 
        report_id: str, 
        form_data: UpdateReportForm
    ) -> Optional[ReportFeedbackModel]:
        try:
            with get_db() as db:
                update_data = {
                    "status": form_data.status,
                    "updated_at": int(time.time())
                }
                
                if form_data.admin_notes:
                    update_data["admin_notes"] = form_data.admin_notes
                
                if form_data.status in ['resolved', 'rejected']:
                    update_data["resolved_at"] = int(time.time())
                
                db.query(ReportFeedback).filter_by(id=report_id).update(update_data)
                db.commit()
                
                report = db.query(ReportFeedback).filter_by(id=report_id).first()
                return ReportFeedbackModel.model_validate(report) if report else None
        except Exception as e:
            log.error(f"更新举报状态失败: {e}")
            return None
    
    def check_rate_limit(self, user_id: Optional[str], ip_address: str) -> bool:
        """检查举报频率限制 - 每小时最多5次"""
        try:
            with get_db() as db:
                current_time = int(time.time())
                hour_ago = current_time - 3600
                
                query = db.query(ReportFeedback).filter(
                    ReportFeedback.created_at > hour_ago
                )
                
                if user_id:
                    query = query.filter(ReportFeedback.user_id == user_id)
                else:
                    query = query.filter(ReportFeedback.ip_address == ip_address)
                
                count = query.count()
                return count < 5
        except Exception as e:
            log.error(f"检查举报频率限制失败: {e}")
            return True  # 默认允许
    
    def delete_report(self, report_id: str) -> bool:
        try:
            with get_db() as db:
                result = db.query(ReportFeedback).filter_by(id=report_id).delete()
                db.commit()
                return result > 0
        except Exception:
            return False

Reports = ReportFeedbackTable()