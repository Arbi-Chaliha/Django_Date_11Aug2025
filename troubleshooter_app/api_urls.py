from django.urls import path
from . import api_views

urlpatterns = [
    # Each Teradata query has its own dedicated API endpoint.
    # The names are clear and consistent for a RESTful design.
    path('teradata/threshold_sup_10450/', api_views.threshold_sup_10450_api, name='api_threshold_sup_10450'),
    path('teradata/threshold_sup_12000/', api_views.threshold_sup_12000_api, name='api_threshold_sup_12000'),
    path('teradata/threshold_sup_5000/', api_views.threshold_sup_5000_api, name='api_threshold_sup_5000'),
    path('teradata/discrete_sup_10/', api_views.discrete_sup_10_api, name='api_discrete_sup_10'),
    path('teradata/discrete_sup_20/', api_views.discrete_sup_20_api, name='api_discrete_sup_20'),
    path('teradata/mcrterrfm_check/', api_views.mcrterrfm_check_api, name='api_mcrterrfm_check'),
    path('teradata/limit_check/', api_views.limit_check_api, name='api_limit_check'),
    path('teradata/status_check/', api_views.status_check_api, name='api_status_check'),
    path('teradata/large_pump/', api_views.large_pump_api, name='api_large_pump'),
    path('teradata/small_pump/', api_views.small_pump_api, name='api_small_pump'),
    path('teradata/mterrstafm_check/', api_views.mterrstafm_check_api, name='api_mterrstafm_check'),
]
