import os
import urllib.parse
import pandas as pd
import duckdb
from rdflib import Graph, Literal, Namespace, RDF, RDFS, URIRef
from rdflib.namespace import OWL, RDF, RDFS, FOAF, XSD, DC, SKOS
from sqlalchemy import create_engine, text
from dotenv import load_dotenv
from django.conf import settings

# --- Data Access and Query Functions ---

def get_teradata_engine():
    """
    Initializes and returns a Teradata engine connection object.
    It handles environment variable loading and connection string creation.
    Returns None if the connection fails.
    """
    load_dotenv()
    user = os.getenv("TERADATA_USER")
    pasw = os.getenv("TERADATA_PASS")
    host = os.getenv("TERADATA_HOST")
    
    if not all([user, pasw, host]):
        print("Error: Teradata credentials missing from .env file.")
        return None

    try:
        encoded_pass = urllib.parse.quote_plus(pasw)
        # We don't use port as it is not needed in the connection string
        td_engine = create_engine(
            f'teradatasql://{user}:{encoded_pass}@{host}/?encryptdata=true'
        )
        print("Teradata engine created successfully.")
        return td_engine
    except Exception as e:
        print(f"Error creating Teradata engine: {e}")
        return None

def load_ontology_graph():
    """
    Loads the ontology graph from the specified TTL file.
    Returns the graph object or None if it fails.
    """
    file_path = os.path.join(settings.BASE_DIR, 'data', 'output_ORA_FNFM_KG.ttl')
    g = Graph()
    try:
        g.parse(file_path, format='turtle')
        print("Ontology loaded successfully.")
        return g
    except Exception as e:
        print(f"Error loading ontology: {e}")
        return None

def get_all_failure_labels(g):
    """
    Queries the ontology graph to get all failure labels.
    """
    query= """
    PREFIX troubleshooting_ora_fnfm_ontology_: <http://www.slb.com/ontologies/Troubleshooting_ORA_FNFM_Ontology_#>
    PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
    SELECT DISTINCT ?failure
    WHERE {
      ?failure_uri a troubleshooting_ora_fnfm_ontology_:Failure ;
      rdfs:label ?failure
    }
    """
    failure_query_result = g.query(query)
    df_failures = pd.DataFrame(failure_query_result, columns=["failure"])
    return df_failures["failure"].tolist()

def get_metadata(td_engine):
    """Fetches the FNFM_FLEET_METADATA table from Teradata."""
    try:
        with td_engine.connect() as conn:
            sql = "SELECT * FROM PRD_RP_PRODUCT_VIEW.FNFM_FLEET_METADATA"
            df = pd.read_sql(sql, conn)
            return df
    except Exception as e:
        print(f"Error fetching metadata: {e}")
        return pd.DataFrame()

def get_partition_id(td_engine, serial_number, job_number, job_start):
    """
    Fetches the partition ID based on user selections.
    """
    try:
        with td_engine.connect() as conn:
            sql = f"""
            SELECT partition_id
            FROM PRD_RP_PRODUCT_VIEW.FNFM_FLEET_METADATA
            WHERE
            serial_number = '{serial_number}' AND
            job_number = '{job_number}' AND
            CAST(job_start AS CHAR(26)) = '{job_start}';"""

            df_partition_id = pd.read_sql(sql, conn)
            if not df_partition_id.empty:
                return df_partition_id.iloc[0, 0]
            return None
    except Exception as e:
        print(f"Error getting partition ID: {e}")
        return None

# --- Ontology Query Functions (from your original view) ---
def execute_query_for_concept(g, concept):
    """
    Executes a SPARQL query to get triples for a given concept.
    """
    query = f"""
    PREFIX troubleshooting_ora_fnfm_ontology_: <http://www.slb.com/ontologies/Troubleshooting_ORA_FNFM_Ontology_#>
    PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
    PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
    SELECT DISTINCT ?subject_label (STRAFTER(STR(?predicate), "#") AS ?predicateName) ?object_label
    WHERE {{
      ?subject_uri ?predicate ?object_uri;
              rdfs:label "{concept}";
              rdfs:label ?subject_label.
      ?subject_uri a ?type_subject.
      ?object_uri a ?type_object;
              rdfs:label ?object_label.
      FILTER (?type_subject IN (troubleshooting_ora_fnfm_ontology_:Failure, troubleshooting_ora_fnfm_ontology_:RootCause, troubleshooting_ora_fnfm_ontology_:Trigger, troubleshooting_ora_fnfm_ontology_:DataChannel) ||
          ?type_object IN (troubleshooting_ora_fnfm_ontology_:Failure, troubleshooting_ora_fnfm_ontology_:RootCause, troubleshooting_ora_fnfm_ontology_:Trigger, troubleshooting_ora_fnfm_ontology_:DataChannel))
      FILTER (?predicate != rdf:type)
    }}
    """
    result = g.query(query)
    labels_list = [(str(row[0]), str(row[1]), str(row[2])) for row in result]
    return labels_list

def graph_search_tuple(g, concept, visited=None, result=None, max_depth=-1, depth=0, depth_results=None):
    """
    Return a dictionary of lists of triples for each depth for a specified concept.
    """
    if visited is None:
        visited = []
    if result is None:
        result = []
    if depth_results is None:
        depth_results = {}

    if max_depth != -1 and depth >= max_depth:
        return depth_results

    if concept in visited:
        return depth_results

    visited.append(concept)

    results_query = execute_query_for_concept(g, concept)

    if depth not in depth_results:
        depth_results[depth] = []
    depth_results[depth].extend([elem for elem in results_query if elem not in depth_results[depth]])

    result.extend([elem for elem in results_query if elem not in result])

    for concept1, message, concept2 in results_query:
        graph_search_tuple(g, concept2, visited, result, max_depth, depth + 1, depth_results)

    return depth_results

# --- Teradata Query Functions (from your original view) ---
# These functions are now cleanly separated in the services layer.
def threshold_sup_10450(conn, partition_id, triple_subject):
    sql = f""" sel sum(error_count) as count_of_error
    from PRD_RP_PRODUCT_VIEW.FNFM_LIMIT_CHECK_PER_JOB
    where xcol = 'MCDIGVLTFM' and (metric_name = 'above_sigma_one'
    or metric_name = 'below_sigma_one') and partition_id = {partition_id}"""
    df = pd.read_sql(sql, conn)
    result_value = df.iloc[0, 0]
    return result_value > 10450 if result_value is not None else False

def threshold_sup_12000(conn, partition_id, triple_subject):
    sql = f""" sel sum(error_count) as sum_error_count
    from PRD_RP_PRODUCT_VIEW.FNFM_LIMIT_CHECK_PER_JOB
    where xcol = 'MCREFVLTFM' and partition_id = {partition_id} """
    df = pd.read_sql(sql, conn)
    result_value = df.iloc[0, 0]
    return result_value is not None and result_value > 12000

def threshold_sup_5000(conn, partition_id, triple_subject):
    sql = f""" sel sum(error_count) as sum_error_count
    from PRD_RP_PRODUCT_VIEW.FNFM_LIMIT_CHECK_PER_JOB
    where (metric_name = 'above_sigma_one' or metric_name = 'below_sigma_one') and xcol = 'MCINVLTFM' and partition_id = {partition_id} """
    df = pd.read_sql(sql, conn)
    result_value = df.iloc[0, 0]
    return result_value > 5000 if result_value is not None else False

def discrete_sup_10(conn, partition_id, triple_subject):
    sql = f""" sel sum(count_error) as count_of_error
    from PRD_RP_PRODUCT_VIEW.FNFM_STATUS_WORDS_AGGREGATED_PER_JOB
    where xcol = '{triple_subject}' and xcol_decoded = 'FNFM_TripPhaseAFM' and partition_id= '{partition_id}' """
    df = pd.read_sql(sql, conn)
    result_value = df.iloc[0, 0]
    return int(result_value) > 10 if result_value is not None else False

def discrete_sup_20(conn, partition_id, triple_subject):
    sql = f""" sel sum(count_error) as count_of_error
    from PRD_RP_PRODUCT_VIEW.FNFM_STATUS_WORDS_AGGREGATED_PER_JOB
    where xcol = '{triple_subject}' and xcol_decoded = 'FNFM_EIPUplinkMessageSend' and partition_id= '{partition_id}' """
    df = pd.read_sql(sql, conn)
    result_value = df.iloc[0, 0]
    return int(result_value) > 20 if result_value is not None else False

def mcrterrfm_check(conn, partition_id, triple_subject):
    sql = f""" sel sum(count_error) as count_of_error
    from PRD_RP_PRODUCT_VIEW.FNFM_STATUS_WORDS_AGGREGATED_PER_JOB
    where xcol = 'MCRTERRFM' and xcol_decoded in ('FNFM_EIPUplinkMessageSend','FNFM_EIPITCMessageSend', 'FNFM_EIPLoopbackMessageSend', 'FNFM_EIPDownlinkMessageReceive') and partition_id= '{partition_id}' """
    df = pd.read_sql(sql, conn)
    result_value = df.iloc[0, 0]
    return int(result_value) > 1 if result_value is not None else False

def limit_check(conn, partition_id, triple_subject):
    sql = f""" sel sum(error_count),min("min"),max("max")
    from PRD_GLBL_DATA_PRODUCTS.FNFM_fleet_timeseries_generic_limit_checks_agg_mavg
    where xcol = '{triple_subject}' and partition_id= '{partition_id}' """
    df = pd.read_sql(sql, conn)
    result_value = df.iloc[0, 0]
    return int(result_value) > 0 if result_value is not None else False

def status_check(conn, partition_id, triple_subject):
    sql = f""" sel partition_id
    from PRD_GLBL_DATA_PRODUCTS.FNFM_fleet_timeseries_generic_status_checks
    where event_name = '{triple_subject}' and partition_id= '{partition_id}' """
    df = pd.read_sql(sql, conn)
    return not df.empty

def large_pump(conn, partition_id, triple_subject):
    sql = f""" sel partition_id
    from PRD_GLBL_DATA_PRODUCTS.FNFM_fleet_timeseries_large_pump_cal_check
    where health_indicator = 'Fail' and partition_id= '{partition_id}' """
    df = pd.read_sql(sql, conn)
    return not df.empty

def small_pump(conn, partition_id, triple_subject):
    sql = f""" sel partition_id
    from PRD_GLBL_DATA_PRODUCTS.FNFM_fleet_timeseries_small_pump_cal_check
    where health_indicator = 'Fail' and partition_id= '{partition_id}' """
    df = pd.read_sql(sql, conn)
    return not df.empty

def mterrstafm_check(conn, partition_id, triple_subject):
    sql = f""" sel sum(count_error) as count_of_error
    from PRD_RP_PRODUCT_VIEW.FNFM_STATUS_WORDS_AGGREGATED_PER_JOB
    where xcol = 'MTERRSTAFM' and xcol_decoded in ('FNFM_FaultIbusFM', 'FNFM_TripPhaseBFM', 'FNFM_TripPhaseCFM', 'FNFM_FaultIbFM', 'FNFM_FaultIaFM', 'FNFM_TripPhaseAFM') and partition_id= '{partition_id}' """
    df = pd.read_sql(sql, conn)
    result_value = df.iloc[0, 0]
    return int(result_value) > 1 if result_value is not None else False

def execute_function_from_the_map(message, mapping, conn, partition_id, datachannel):
    """Execution of the function."""
    if message in mapping:
        return mapping[message](conn, partition_id, datachannel)

def recursive_execute_function(dict_tuple_result, mapping, conn, partition_id):
    """Recursive execution of all functions."""
    result_list = []
    all_tuples = [t for tuples in dict_tuple_result.values() for t in tuples]
    df_tuples = pd.DataFrame(all_tuples, columns=['Subject', 'Predicate', 'Object'])
    query_trigger_datachannel = """
    SELECT DISTINCT t1.Object AS Trigger, t2.Predicate AS Consume, t2.Object AS DataChannel
    FROM df_tuples t1
    JOIN df_tuples t2 ON t1.Object = t2.Subject
    WHERE t1.Predicate = 'isTriggeredBy' AND t2.Predicate = 'consume'
    """
    result_df = duckdb.query(query_trigger_datachannel).to_df()
    for index, row in result_df.iterrows():
        function = row.iloc[0]
        consume = row.iloc[1]
        datachannel = row.iloc[2]
        result = execute_function_from_the_map(function, mapping, conn, partition_id, datachannel)
        result_list.append((function, consume, datachannel, result))
    df = pd.DataFrame(result_list, columns=['Subject', 'Predicate', 'Object', 'Status'])
    return df

def get_root_cause_analysis(df_clean, selected_failure):
    """
    Analyzes the clean DataFrame to identify root causes and their triggers.
    """
    root_cause_table_data = []
    all_tuples = [tuple(x) for x in df_clean.values]
    df_clean_tuples = pd.DataFrame(all_tuples, columns=df_clean.columns)

    query_rootcause = f"""
    SELECT Object
    FROM df_clean_tuples
    WHERE Subject = '{selected_failure}' AND Predicate = 'hasRootCause'
    """
    rootcause_df = duckdb.query(query_rootcause).to_df()

    if not rootcause_df.empty:
        for root_cause in rootcause_df["Object"]:
            query_trigger = f"""
            SELECT Object
            FROM df_clean_tuples
            WHERE Subject = '{root_cause}' AND Predicate = 'isTriggeredBy'
            """
            trigger_df = duckdb.query(query_trigger).to_df()

            if not trigger_df.empty:
                for trigger_value in trigger_df["Object"]:
                    query_datachannel = f"""
                    SELECT DISTINCT Object, Status
                    FROM df_clean_tuples
                    WHERE Subject='{trigger_value}' AND Predicate='consume' AND Status=True
                    """
                    datachannel_df = duckdb.query(query_datachannel).to_df()

                    if not datachannel_df.empty:
                        for _, row in datachannel_df.iterrows():
                            symbol = "🔴"
                            root_cause_table_data.append([root_cause, trigger_value, f"{row['Object']} {symbol}"])

    return root_cause_table_data

def execute_troubleshooting_logic(g, td_engine, partition_id, selected_failure):
    """
    Main function to execute the core troubleshooting logic.
    """
    try:
        with td_engine.connect() as conn:
            dic_tuple_result = graph_search_tuple(g, selected_failure, max_depth=-1)
            mapping_function = {
                "FNFM Uplink telemetry check": status_check,
                "FNFM LIN device check": status_check,
                "FNFM CAN device check": status_check,
                "FNFM Motor Error Status": mterrstafm_check,
                "FNFM Solenoid PHM HALL Voltage": limit_check,
                "FNFM Solenoid PHM Digital Voltage": limit_check,
                "FNFM Solenoid PHM LIN Voltage ADC": limit_check,
                "FNFM Master Controller Reference Voltage": limit_check,
                "FNFM Master Controller Digital Voltage": limit_check,
                "FNFM Master Controller Input Voltage": limit_check,
                "FNFM Master Controller Core Voltage": limit_check,
                "FNFM Master Controller EIP Core Voltage": limit_check,
                "FNFM Master Controller EIP Digital Voltage": limit_check,
                "FNFM LVPS Digital Voltage": limit_check,
                "FNFM LVPS Positive Analog Voltage": limit_check,
                "FNFM LVPS Negative Analog Voltage": limit_check,
                "FNFM Small pump calibration check": small_pump,
                "FNFM Large pump calibration check": large_pump
            }

            result_df_functions = recursive_execute_function(dic_tuple_result, mapping_function, conn, partition_id)

            all_tuples = [t for tuples in dic_tuple_result.values() for t in tuples]
            df_tuples = pd.DataFrame(all_tuples, columns=['Subject', 'Predicate', 'Object'])
            df_final = pd.merge(df_tuples, result_df_functions, on=["Subject", "Predicate", "Object"], how="left")
            df_clean = df_final[df_final["Status"].apply(lambda x: x is not None)]
            return df_clean, dic_tuple_result

    except Exception as e:
        print(f"Error in core troubleshooting logic: {e}")
        return pd.DataFrame(), {}