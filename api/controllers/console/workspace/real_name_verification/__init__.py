from flask import Blueprint
from libs.external_api import ExternalApi

from .real_name_verification import (
    RealNameVerificationSubmitApi,
    RealNameVerificationStatusApi,
    RealNameVerificationResubmitApi,
    RealNameVerificationApproveApi,
    RealNameVerificationRejectApi,
    RealNameVerificationPendingApi,
    RealNameVerificationStatsApi,
)

bp = Blueprint('real_name_verification', __name__, url_prefix='/console/api')
api = ExternalApi(bp)

# User endpoints - for regular users
api.add_resource(RealNameVerificationSubmitApi, '/real-name-verification/submit')
api.add_resource(RealNameVerificationStatusApi, '/real-name-verification/status')
api.add_resource(RealNameVerificationResubmitApi, '/real-name-verification/<string:verification_id>/resubmit')

# Admin endpoints - for admin users
api.add_resource(RealNameVerificationApproveApi, '/real-name-verification/<string:verification_id>/approve')
api.add_resource(RealNameVerificationRejectApi, '/real-name-verification/<string:verification_id>/reject')
api.add_resource(RealNameVerificationPendingApi, '/real-name-verification/pending')
api.add_resource(RealNameVerificationStatsApi, '/real-name-verification/stats')