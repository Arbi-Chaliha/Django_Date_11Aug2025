from django.http import JsonResponse
from .services import (
    get_teradata_engine,
    threshold_sup_10450,
    threshold_sup_12000,
    threshold_sup_5000,
    discrete_sup_10,
    discrete_sup_20,
    mcrterrfm_check,
    limit_check,
    status_check,
    large_pump,
    small_pump,
    mterrstafm_check,
)

# Initialize the Teradata engine once at the app's startup.
td_engine = get_teradata_engine()

# A generic function to handle API requests and errors cleanly.
def _teradata_query_api(request, query_func):
    """
    Helper function to process a generic Teradata query request.
    It extracts parameters and calls the provided service function.
    """
    if td_engine is None:
        return JsonResponse({'error': 'Teradata connection is not available.'}, status=500)

    # We expect these parameters to be passed in the URL as query parameters.
    partition_id = request.GET.get('partition_id')
    triple_subject = request.GET.get('triple_subject')

    if not all([partition_id, triple_subject]):
        return JsonResponse({'error': 'Missing required parameters: partition_id and triple_subject.'}, status=400)

    try:
        with td_engine.connect() as conn:
            result = query_func(conn, partition_id, triple_subject)
            return JsonResponse({'result': result})
    except Exception as e:
        # Proper error handling to provide helpful feedback.
        return JsonResponse({'error': f'An error occurred: {e}'}, status=500)


# --- Dedicated API Views for each Teradata Query ---
def threshold_sup_10450_api(request):
    """API endpoint for the threshold_sup_10450 query."""
    return _teradata_query_api(request, threshold_sup_10450)

def threshold_sup_12000_api(request):
    """API endpoint for the threshold_sup_12000 query."""
    return _teradata_query_api(request, threshold_sup_12000)

def threshold_sup_5000_api(request):
    """API endpoint for the threshold_sup_5000 query."""
    return _teradata_query_api(request, threshold_sup_5000)

def discrete_sup_10_api(request):
    """API endpoint for the discrete_sup_10 query."""
    return _teradata_query_api(request, discrete_sup_10)

def discrete_sup_20_api(request):
    """API endpoint for the discrete_sup_20 query."""
    return _teradata_query_api(request, discrete_sup_20)

def mcrterrfm_check_api(request):
    """API endpoint for the mcrterrfm_check query."""
    return _teradata_query_api(request, mcrterrfm_check)

def limit_check_api(request):
    """API endpoint for the limit_check query."""
    return _teradata_query_api(request, limit_check)

def status_check_api(request):
    """API endpoint for the status_check query."""
    return _teradata_query_api(request, status_check)

def large_pump_api(request):
    """API endpoint for the large_pump query."""
    return _teradata_query_api(request, large_pump)

def small_pump_api(request):
    """API endpoint for the small_pump query."""
    return _teradata_query_api(request, small_pump)

def mterrstafm_check_api(request):
    """API endpoint for the mterrstafm_check query."""
    return _teradata_query_api(request, mterrstafm_check)
