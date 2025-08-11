import json
import os
import shutil
import pandas as pd
from pyvis.network import Network
from django.shortcuts import render
from django.conf import settings
from django.http import JsonResponse
from .forms import TroubleshooterForm
from .services import (
    get_teradata_engine,
    load_ontology_graph,
    get_all_failure_labels,
    get_metadata,
    get_partition_id,
    execute_troubleshooting_logic,
    get_root_cause_analysis
)

# --- Initialize Resources (outside of view to avoid re-initialization on every request) ---
# It's better to load these once. However, for a real production environment,
# you would need to manage this with a connection pool or a more robust system.
# For this example, we keep it simple for demonstration.
td_engine = get_teradata_engine()
g = load_ontology_graph()

# --- Main Django View ---
def troubleshooter_view(request):
    """
    Handles the main web page for the troubleshooter app.
    It orchestrates the form, data processing, and rendering of results.
    """
    form = TroubleshooterForm()
    context = {
        'form': form,
        'messages': [],
        'failure_list': [],
        'partition_id': None,
        'df_clean_html': None,
        'root_cause_table_html': None,
        'graph_html_path': None,
    }

    # If the Teradata engine failed to initialize, we can't do anything.
    if td_engine is None:
        context['messages'].append("Error: Could not connect to Teradata. Please check credentials and connection settings.")
        return render(request, 'troubleshooter.html', context)

    try:
        # Get the list of failures from the ontology to populate the selectbox.
        context['failure_list'] = get_all_failure_labels(g)

        if request.method == 'POST':
            form = TroubleshooterForm(request.POST)

            # Get the metadata to populate the form fields
            df_metadata = get_metadata(td_engine)
            
            selected_serial_number = request.POST.get('serial_number')
            selected_job_number = request.POST.get('job_number')
            selected_job_start = request.POST.get('job_start')
            selected_failure = request.POST.get('failure_selectbox')

            if selected_serial_number and selected_job_number and selected_job_start and selected_failure:
                # Get the partition_id from the metadata.
                partition_id = get_partition_id(td_engine, selected_serial_number, selected_job_number, selected_job_start)

                if partition_id:
                    context['partition_id'] = partition_id
                    context['messages'].append(f"The partition_id associated with your chosen criteria is {partition_id}")

                    # --- Execute the core logic via services ---
                    df_clean, dic_tuple_result = execute_troubleshooting_logic(g, td_engine, partition_id, selected_failure)
                    context['df_clean_html'] = df_clean.to_html(classes='table table-striped table-bordered', index=False) if not df_clean.empty else None

                    # --- Root Cause Analysis Table via services ---
                    root_cause_table_data = get_root_cause_analysis(df_clean, selected_failure)
                    context['root_cause_table_html'] = pd.DataFrame(root_cause_table_data, columns=["Root Cause", "Trigger", "Data Channel"]).to_html(classes='table table-striped table-bordered', index=False) if root_cause_table_data else None

                    # --- Pyvis Graph Generation ---
                    # The view is responsible for the final output, like the graph HTML.
                    if not df_clean.empty:
                        net = Network(height="1100px", width="100%", directed=True, notebook=True)
                        for _, row in df_clean.iterrows():
                            subject = row['Subject']
                            predicate = row['Predicate']
                            object_node = row['Object']
                            status = row['Status']

                            # Color logic is kept here as it's part of the view's presentation.
                            color_subject = "#A7C7E7"
                            color_object = "#A7C7E7"
                            color_predicate = "#A7C7E7"
                            title_subject = f"name:{subject}"
                            title_object = f"name:{object_node}"
                            title_predicate = f"name:{predicate}"

                            if predicate == "hasRootCause":
                                color_subject = "#FFCC99"
                                color_object = "#C5A3FF"
                                title_subject = f"type:failure, name:{subject}"
                                title_object = f"type:Root Cause, name:{object_node}"
                            elif predicate == "isTriggeredBy":
                                color_subject = "#C5A3FF"
                                color_object = "#D2B48C"
                                title_subject = f"type:Root Cause, name:{subject}"
                                title_object = f"type:Trigger, name:{object_node}, value:{status}"
                            elif predicate == "consume":
                                color_subject = "#D2B48C"
                                title_subject = f"type:trigger, name:{subject}"
                                title_object = f"type:data channel, name:{object_node}"
                                if status == False:
                                    color_object = "green"
                                    color_predicate = "green"
                                elif status == True:
                                    color_object = "red"
                                    color_predicate = "red"
                            
                            net.add_node(subject, color=color_subject, label=subject, title=title_subject)
                            net.add_node(object_node, color=color_object, label=object_node, title=title_object)
                            net.add_edge(subject, object_node, color=color_predicate, title=title_predicate)

                        net.force_atlas_2based(gravity=-50, central_gravity=0.01, spring_length=200, spring_strength=0.05)
                        
                        graph_filename = f"graph_{partition_id}.html"
                        graph_output_path = os.path.join(settings.STATICFILES_DIRS[0], 'graphs', graph_filename)
                        net.save_graph(graph_output_path)
                        context['graph_html_path'] = os.path.join(settings.STATIC_URL, 'graphs', graph_filename)
                else:
                    context['messages'].append("Error: Could not find partition_id for the selected criteria.")
            else:
                context['messages'].append("Please select all fields (Serial Number, Job Number, Start Job, and Failure) to proceed.")
        
    except Exception as e:
        context['messages'].append(f"An unexpected error occurred: {e}")
    
    return render(request, 'troubleshooter.html', context)


# --- New API View Functions ---
def get_form_choices(request):
    """
    API endpoint to dynamically get form choices based on a parent selection.
    This replaces the full page form submission for dropdown updates.
    """
    parent_field = request.GET.get('parent_field')
    parent_value = request.GET.get('parent_value')

    if not parent_field or not td_engine:
        return JsonResponse({'choices': []})
    
    try:
        df_metadata = get_metadata(td_engine)
        choices = []
        if parent_field == 'serial_number':
            choices = sorted([(str(x), str(x)) for x in df_metadata["serial_number"].fillna('NaN').unique()])
        elif parent_field == 'job_number' and parent_value:
            df_serial_number = df_metadata[df_metadata["serial_number"] == parent_value]
            choices = sorted([(str(x), str(x)) for x in df_serial_number["job_number"].fillna('NaN').unique()])
        elif parent_field == 'job_start' and parent_value:
            df_serial_and_job_number = df_metadata[df_metadata["job_number"] == parent_value]
            choices = sorted([(str(x), str(x)) for x in df_serial_and_job_number["job_start"].fillna('NaN').unique()])

        return JsonResponse({'choices': choices})
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


def get_troubleshooter_data(request):
    """
    New API endpoint to fetch the processed troubleshooting data as JSON.
    A front-end could use this to render a dynamic graph without a page reload.
    """
    selected_failure = request.GET.get('failure')
    partition_id = request.GET.get('partition_id')

    if not selected_failure or not partition_id:
        return JsonResponse({'error': 'Missing required parameters'}, status=400)

    try:
        df_clean, dic_tuple_result = execute_troubleshooting_logic(g, td_engine, partition_id, selected_failure)
        
        # Convert DataFrame to a list of dictionaries for JSON serialization
        data = df_clean.to_dict('records')
        
        return JsonResponse({'data': data})
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

