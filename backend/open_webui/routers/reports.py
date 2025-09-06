import logging
import os
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, Request, UploadFile, File, status
from fastapi.responses import JSONResponse

from open_webui.models.reports import (
    Reports,
    CreateReportForm,
    UpdateReportForm,
    ReportFeedbackModel,
    ReportListResponse
)
from open_webui.utils.auth import get_current_user, get_admin_user
from open_webui.constants import ERROR_MESSAGES
from open_webui.env import SRC_LOG_LEVELS

router = APIRouter()
log = logging.getLogger(__name__)
log.setLevel(SRC_LOG_LEVELS["MAIN"])

# 举报分类定义
REPORT_CATEGORIES = {
    'inappropriate': '不当内容',
    'technical': '技术问题', 
    'copyright': '版权问题',
    'spam': '垃圾信息',
    'misinformation': '虚假信息',
    'other': '其他问题'
}

############################
# 用户举报接口
############################

@router.post("/", response_model=ReportFeedbackModel)
async def create_report(
    request: Request,
    form_data: CreateReportForm,
    user=Depends(get_current_user)
):
    """创建新的举报反馈"""
    
    # 验证举报分类
    if form_data.category not in REPORT_CATEGORIES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="无效的举报分类"
        )
    
    # 获取用户IP和User-Agent
    client_ip = request.client.host if request.client else None
    user_agent = request.headers.get("user-agent", "")
    
    # 检查举报频率限制
    if not Reports.check_rate_limit(user.id, client_ip):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="举报过于频繁，请稍后再试"
        )
    
    report = Reports.create_report(
        form_data,
        user_id=user.id,
        ip_address=client_ip,
        user_agent=user_agent
    )
    
    if not report:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="创建举报失败"
        )
    
    return report

@router.post("/anonymous", response_model=ReportFeedbackModel)
async def create_anonymous_report(
    request: Request,
    form_data: CreateReportForm
):
    """创建匿名举报反馈"""
    
    # 验证举报分类
    if form_data.category not in REPORT_CATEGORIES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="无效的举报分类"
        )
    
    # 获取用户IP和User-Agent
    client_ip = request.client.host if request.client else None
    user_agent = request.headers.get("user-agent", "")
    
    # 检查匿名举报频率限制
    if not Reports.check_rate_limit(None, client_ip):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="举报过于频繁，请稍后再试"
        )
    
    report = Reports.create_report(
        form_data,
        user_id=None,
        ip_address=client_ip,
        user_agent=user_agent
    )
    
    if not report:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="创建举报失败"
        )
    
    return report

@router.get("/categories")
async def get_report_categories():
    """获取举报分类列表"""
    return {"categories": REPORT_CATEGORIES}

@router.get("/my", response_model=List[ReportFeedbackModel])
async def get_my_reports(user=Depends(get_current_user)):
    """获取当前用户的举报记录"""
    reports = Reports.get_reports_by_user(user.id)
    return reports

@router.get("/{report_id}", response_model=ReportFeedbackModel)
async def get_report_detail(
    report_id: str,
    user=Depends(get_current_user)
):
    """获取举报详情"""
    report = Reports.get_report_by_id(report_id)
    
    if not report:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="举报记录不存在"
        )
    
    # 检查权限 - 只能查看自己的举报或管理员
    if report.user_id != user.id and user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="无权访问该举报记录"
        )
    
    return report

############################
# 管理员接口
############################

@router.get("/admin/all", response_model=ReportListResponse)
async def get_all_reports(
    status: Optional[str] = None,
    skip: int = 0,
    limit: int = 50,
    user=Depends(get_admin_user)
):
    """管理员获取所有举报记录"""
    return Reports.get_all_reports(status, skip, limit)

@router.put("/admin/{report_id}", response_model=ReportFeedbackModel)
async def update_report_status(
    report_id: str,
    form_data: UpdateReportForm,
    user=Depends(get_admin_user)
):
    """管理员更新举报状态"""
    
    valid_statuses = ['pending', 'processing', 'resolved', 'rejected']
    if form_data.status not in valid_statuses:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="无效的状态值"
        )
    
    report = Reports.update_report_status(report_id, form_data)
    
    if not report:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="举报记录不存在"
        )
    
    return report

@router.delete("/admin/{report_id}")
async def delete_report(
    report_id: str,
    user=Depends(get_admin_user)
):
    """管理员删除举报记录"""
    success = Reports.delete_report(report_id)
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="举报记录不存在"
        )
    
    return {"message": "举报记录已删除"}

############################
# 截图上传接口
############################

@router.post("/upload-screenshot")
async def upload_screenshot(
    file: UploadFile = File(...),
    user=Depends(get_current_user)
):
    """上传举报截图"""
    
    # 验证文件类型
    allowed_types = ['image/jpeg', 'image/png', 'image/webp', 'image/gif']
    if file.content_type not in allowed_types:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="不支持的图片格式"
        )
    
    # 验证文件大小 (最大5MB)
    if file.size and file.size > 5 * 1024 * 1024:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="图片大小不能超过5MB"
        )
    
    try:
        # 创建上传目录
        upload_dir = "data/uploads/reports"
        os.makedirs(upload_dir, exist_ok=True)
        
        # 生成唯一文件名
        import uuid
        file_extension = file.filename.split('.')[-1] if file.filename else 'jpg'
        unique_filename = f"{uuid.uuid4()}.{file_extension}"
        file_path = os.path.join(upload_dir, unique_filename)
        
        # 保存文件
        content = await file.read()
        with open(file_path, 'wb') as f:
            f.write(content)
        
        return {
            "filename": unique_filename,
            "path": file_path,
            "size": len(content)
        }
    
    except Exception as e:
        log.error(f"上传截图失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="上传失败"
        )