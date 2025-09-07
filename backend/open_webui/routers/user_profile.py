from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File
from fastapi.responses import JSONResponse
from open_webui.models.user_profile import (
    UserProfileForm,
    UserProfileUpdateForm, 
    UserProfileResponse,
    UserProfiles
)
from open_webui.models.users import Users
from open_webui.utils.auth import get_current_user
from open_webui.constants import ERROR_MESSAGES
import os
import uuid
import logging
from typing import Optional
import aiofiles
import re

log = logging.getLogger(__name__)
router = APIRouter(prefix="/profile", tags=["user_profile"])

UPLOAD_DIR = "data/uploads/id_cards"

####################
# Helper Functions
####################

def validate_id_card(id_card: str) -> bool:
    """验证身份证号码格式"""
    if not id_card or len(id_card) != 18:
        return False
    
    # 简单的身份证号格式验证
    pattern = r'^[1-9]\d{5}(18|19|20)\d{2}((0[1-9])|(1[0-2]))(([0-2][1-9])|10|20|30|31)\d{3}[0-9Xx]$'
    return bool(re.match(pattern, id_card))

def validate_real_name(real_name: str) -> bool:
    """验证真实姓名格式"""
    if not real_name or len(real_name) < 2 or len(real_name) > 20:
        return False
    
    # 中文姓名格式验证
    pattern = r'^[\u4e00-\u9fa5·]{2,20}$'
    return bool(re.match(pattern, real_name))

async def save_upload_file(file: UploadFile, user_id: str, file_type: str) -> str:
    """保存上传的身份证照片"""
    if not file.filename:
        raise ValueError("文件名为空")
    
    # 确保上传目录存在
    os.makedirs(UPLOAD_DIR, exist_ok=True)
    
    # 生成唯一文件名
    file_extension = os.path.splitext(file.filename)[1].lower()
    if file_extension not in ['.jpg', '.jpeg', '.png']:
        raise ValueError("不支持的文件格式")
    
    filename = f"{user_id}_{file_type}_{uuid.uuid4()}{file_extension}"
    filepath = os.path.join(UPLOAD_DIR, filename)
    
    # 保存文件
    async with aiofiles.open(filepath, 'wb') as f:
        content = await file.read()
        if len(content) > 5 * 1024 * 1024:  # 5MB限制
            raise ValueError("文件大小超过限制")
        await f.write(content)
    
    return filepath

####################
# API Endpoints
####################

@router.get("/", response_model=UserProfileResponse)
async def get_user_profile(user=Depends(get_current_user)):
    """获取用户实名认证资料"""
    try:
        profile = UserProfiles.get_profile(user.id)
        if not profile:
            # 如果没有资料，返回默认结构
            return UserProfileResponse(
                user_id=user.id,
                verified=False,
                verification_status="not_started",
                has_id_card_photos=False,
                created_at=0,
                updated_at=0
            )
        
        return profile
    except Exception as e:
        log.error(f"获取用户资料错误: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ERROR_MESSAGES.DEFAULT()
        )

@router.post("/", response_model=dict)
async def create_user_profile(form_data: UserProfileForm, user=Depends(get_current_user)):
    """创建用户实名认证资料"""
    try:
        # 验证输入数据
        if not validate_real_name(form_data.real_name):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="姓名格式不正确，请输入2-20位中文姓名"
            )
        
        if not validate_id_card(form_data.id_card):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="身份证号码格式不正确"
            )
        
        # 检查是否已存在
        existing_profile = UserProfiles.get_profile(user.id)
        if existing_profile and existing_profile.verification_status != "not_started":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="实名认证资料已存在，请使用更新接口"
            )
        
        # 创建认证资料
        profile = UserProfiles.create_profile(
            user_id=user.id,
            real_name=form_data.real_name,
            id_card=form_data.id_card
        )
        
        if not profile:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="创建实名认证资料失败"
            )
        
        return {"message": "实名认证资料创建成功", "status": "pending"}
    
    except HTTPException:
        raise
    except Exception as e:
        log.error(f"创建用户资料错误: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ERROR_MESSAGES.DEFAULT()
        )

@router.put("/", response_model=dict)
async def update_user_profile(form_data: UserProfileUpdateForm, user=Depends(get_current_user)):
    """更新用户实名认证资料"""
    try:
        # 验证输入数据
        if form_data.real_name and not validate_real_name(form_data.real_name):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="姓名格式不正确，请输入2-20位中文姓名"
            )
        
        if form_data.id_card and not validate_id_card(form_data.id_card):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="身份证号码格式不正确"
            )
        
        # 更新认证资料
        success = UserProfiles.update_profile(user.id, form_data)
        if not success:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="更新实名认证资料失败，请先创建资料"
            )
        
        return {"message": "实名认证资料更新成功，认证状态已重置为待审核"}
    
    except HTTPException:
        raise
    except Exception as e:
        log.error(f"更新用户资料错误: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ERROR_MESSAGES.DEFAULT()
        )

@router.post("/upload-id-card", response_model=dict)
async def upload_id_card_photo(
    file_type: str,  # "front" 或 "back"
    file: UploadFile = File(...),
    user=Depends(get_current_user)
):
    """上传身份证照片"""
    try:
        if file_type not in ["front", "back"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="文件类型必须是 front 或 back"
            )
        
        if not file.filename:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="请选择要上传的文件"
            )
        
        # 保存文件
        filepath = await save_upload_file(file, user.id, file_type)
        
        # 更新数据库记录
        if file_type == "front":
            success = UserProfiles.update_id_card_photos(user.id, front_path=filepath)
        else:
            success = UserProfiles.update_id_card_photos(user.id, back_path=filepath)
        
        if not success:
            # 如果数据库更新失败，删除已上传的文件
            try:
                os.remove(filepath)
            except:
                pass
            
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="文件上传失败"
            )
        
        return {
            "message": f"身份证{'正面' if file_type == 'front' else '背面'}照片上传成功",
            "file_path": filepath
        }
    
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        log.error(f"上传身份证照片错误: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ERROR_MESSAGES.DEFAULT()
        )

@router.get("/verification-status", response_model=dict)
async def get_verification_status(user=Depends(get_current_user)):
    """获取实名认证状态"""
    try:
        profile = UserProfiles.get_profile(user.id)
        if not profile:
            return {
                "verified": False,
                "status": "not_started",
                "message": "尚未开始实名认证"
            }
        
        status_messages = {
            "not_started": "尚未开始实名认证",
            "pending": "实名认证审核中",
            "approved": "实名认证已通过",
            "rejected": "实名认证被拒绝，请重新提交"
        }
        
        return {
            "verified": profile.verified,
            "status": profile.verification_status,
            "message": status_messages.get(profile.verification_status, "未知状态"),
            "verified_at": profile.verified_at
        }
    
    except Exception as e:
        log.error(f"获取认证状态错误: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ERROR_MESSAGES.DEFAULT()
        )