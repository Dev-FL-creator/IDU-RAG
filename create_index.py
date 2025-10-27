# create_index_single.py
import os, sys, json, argparse
from typing import List
from azure.core.credentials import AzureKeyCredential
from azure.core.exceptions import HttpResponseError
from azure.search.documents.indexes import SearchIndexClient
from azure.search.documents.indexes.models import (
    SearchIndex, SimpleField, SearchableField, SearchField, SearchFieldDataType,
    VectorSearch, HnswAlgorithmConfiguration, HnswParameters, VectorSearchAlgorithmKind, VectorSearchProfile
)


def create_index(config_path: str, force: bool=False):
    with open(config_path, "r", encoding="utf-8") as f:
        cfg = json.load(f)

    endpoint = f"https://{cfg['search_service_name']}.search.windows.net"
    api_key = cfg["search_api_key"]
    index_name = cfg["index_name"]
    dims = int(cfg["embedding_dimensions"])
    metric = cfg.get("vector_metric", "cosine")
    search_api_version = cfg.get("search_api_version", "2024-07-01")

    client = SearchIndexClient(endpoint=endpoint, credential=AzureKeyCredential(api_key), api_version=search_api_version)
    existing: List[str] = [ix.name for ix in client.list_indexes()]
    if index_name in existing:
        if force:
            print(f"[info] deleting existing index: {index_name}")
            client.delete_index(index_name)
        else:
            print(f"[skip] index exists: {index_name}")
            return

    vector_search = VectorSearch(
        algorithms=[
            HnswAlgorithmConfiguration(
                name="hnsw-single",
                kind=VectorSearchAlgorithmKind.HNSW,
                parameters=HnswParameters(m=4, ef_construction=400, ef_search=500, metric=metric),
            )
        ],
        profiles=[VectorSearchProfile(name="vpf-single", algorithm_configuration_name="hnsw-single")]
    )

    fields = [
        # keys & provenance
        SimpleField(name="id", type=SearchFieldDataType.String, key=True, filterable=True, sortable=True),
        SimpleField(name="source_id", type=SearchFieldDataType.String, filterable=True, sortable=True),
        SimpleField(name="chunk_index", type=SearchFieldDataType.Int32, filterable=True, sortable=True),

        # content & vector
        SearchableField(name="content", type=SearchFieldDataType.String, analyzer_name="standard.lucene"),
        SimpleField(name="filepath", type=SearchFieldDataType.String, filterable=True),
        SimpleField(name="page_from", type=SearchFieldDataType.Int32, filterable=True, sortable=True),
        SimpleField(name="page_to", type=SearchFieldDataType.Int32, filterable=True, sortable=True),
        SearchField(
            name="content_vector",
            type=SearchFieldDataType.Collection(SearchFieldDataType.Single),
            searchable=True,  # your service requires True
            filterable=False, sortable=False, facetable=False,
            vector_search_dimensions=dims,
            vector_search_profile_name="vpf-single",
        ),

        # -------- structured org fields (duplicated on every chunk) --------
        SearchableField(name="org_name", type=SearchFieldDataType.String, filterable=True, sortable=True, facetable=True),
        SearchableField(name="country", type=SearchFieldDataType.String, filterable=True, facetable=True),
        SearchableField(name="address", type=SearchFieldDataType.String, filterable=True),
        SimpleField(name="founded_year", type=SearchFieldDataType.Int32, filterable=True, sortable=True),
        SimpleField(name="size", type=SearchFieldDataType.String, filterable=True, facetable=True),
        SearchableField(name="industry", type=SearchFieldDataType.String, filterable=True, facetable=True),
        SimpleField(name="is_DU_member", type=SearchFieldDataType.Boolean, filterable=True),
        SearchableField(name="website", type=SearchFieldDataType.String, filterable=True, sortable=True),

        SearchField(name="members_name",  type=SearchFieldDataType.Collection(SearchFieldDataType.String),
                    searchable=True, filterable=True),
        SearchField(name="members_title", type=SearchFieldDataType.Collection(SearchFieldDataType.String),
                    searchable=True, filterable=True),
        SearchField(name="members_role",  type=SearchFieldDataType.Collection(SearchFieldDataType.String),
                    searchable=True, filterable=True),

        SearchField(name="facilities_name",  type=SearchFieldDataType.Collection(SearchFieldDataType.String),
                    searchable=True, filterable=True),
        SearchField(name="facilities_type",  type=SearchFieldDataType.Collection(SearchFieldDataType.String),
                    searchable=True, filterable=True),
        SearchField(name="facilities_usage", type=SearchFieldDataType.Collection(SearchFieldDataType.String),
                    searchable=True, filterable=True),

        SearchField(name="capabilities", type=SearchFieldDataType.Collection(SearchFieldDataType.String),
                    searchable=True, filterable=True, facetable=True),
        SearchField(name="projects",     type=SearchFieldDataType.Collection(SearchFieldDataType.String),
                    searchable=True, filterable=True),
        SearchField(name="awards",       type=SearchFieldDataType.Collection(SearchFieldDataType.String),
                    searchable=True, filterable=True),
        SearchField(name="services",     type=SearchFieldDataType.Collection(SearchFieldDataType.String),
                    searchable=True, filterable=True),

        SearchField(name="contacts_name",  type=SearchFieldDataType.Collection(SearchFieldDataType.String),
                    searchable=True, filterable=True),
        SearchField(name="contacts_email", type=SearchFieldDataType.Collection(SearchFieldDataType.String),
                    searchable=False, filterable=True),
        SearchField(name="contacts_phone", type=SearchFieldDataType.Collection(SearchFieldDataType.String),
                    searchable=False, filterable=True),

        SearchField(name="addresses", type=SearchFieldDataType.Collection(SearchFieldDataType.String),
                    searchable=True, filterable=True),
        SearchableField(name="notes", type=SearchFieldDataType.String),
    ]

    index = SearchIndex(name=index_name, fields=fields, vector_search=vector_search)
    try:
        client.create_index(index)
        print(f"[ok] created index: {index_name} (dims={dims}, metric={metric})")
    except HttpResponseError as e:
        print("[error] create index failed:", e)
        raise

if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("config", help="config.json")
    p.add_argument("--force", action="store_true")
    a = p.parse_args()
    if not os.path.exists(a.config): sys.exit("[error] missing config")
    create_index(a.config, force=a.force)
