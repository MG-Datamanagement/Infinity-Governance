#!/bin/bash
set -e

# Load .env if present (export each var so they're available here)
if [ -f .env ]; then
  set -a
  source .env
  set +a
fi

CORE=app_search_core
SOLR_HOST="${SOLR_HOST:-localhost}"
SOLR_PORT="${SOLR_PORT:-8983}"
SOLR_URI="http://${SOLR_HOST}:${SOLR_PORT}/solr/${CORE}/schema"

echo "Configuring Solr schema at ${SOLR_URI}..."

field_exists() {
  local field_name=$1
  curl -s "${SOLR_URI}" | grep -q "\"${field_name}\""
  return $?
}

add_or_replace_field() {
  local name=$1
  local type=$2
  local stored=$3
  local multi=${4:-false}

  if field_exists "$name"; then
    echo "Replacing field: ${name}"
    body="{
      \"replace-field\": {
        \"name\": \"${name}\",
        \"type\": \"${type}\",
        \"stored\": ${stored},
        \"multiValued\": ${multi}
      }
    }"
  else
    echo "Adding field: ${name}"
    body="{
      \"add-field\": {
        \"name\": \"${name}\",
        \"type\": \"${type}\",
        \"stored\": ${stored},
        \"multiValued\": ${multi}
      }
    }"
  fi

  curl -s -X POST -H "Content-Type: application/json" -d "${body}" "${SOLR_URI}"
  echo
}

add_copy_field() {
  local source=$1
  local dest=$2
  body="{\"add-copy-field\": {\"source\": \"${source}\", \"dest\": \"${dest}\"}}"
  curl -s -X POST -H "Content-Type: application/json" -d "${body}" "${SOLR_URI}"
  echo
}

# ── Identity & routing ─────────────────────────────────────────────────────────
add_or_replace_field "entity_type"     "string"        true  false   # CATALOG, COLUMN, DOMAIN, TAG, GLOSSARY_TERM, SOURCE, OWNER
add_or_replace_field "entity_id"       "string"        true  false   # UUID from PG

# ── Common text fields ─────────────────────────────────────────────────────────
add_or_replace_field "name"            "string"        true  false
add_or_replace_field "display_name"    "string"        true  false
add_or_replace_field "description"     "text_general"  true  false

# ── CATALOG-specific ───────────────────────────────────────────────────────────
add_or_replace_field "full_name"       "string"        true  false   # db.schema.table
add_or_replace_field "database_name"   "string"        true  false
add_or_replace_field "schema_name"     "string"        true  false
add_or_replace_field "table_name"      "string"        true  false
add_or_replace_field "catalog_type"    "string"        true  false   # table | view
add_or_replace_field "catalog_status"  "string"        true  false   # healthy | warning | risk
add_or_replace_field "row_count"       "plong"         true  false
add_or_replace_field "source_id"       "string"        true  false
add_or_replace_field "source_name"     "string"        true  false

# ── COLUMN-specific ────────────────────────────────────────────────────────────
add_or_replace_field "catalog_id"      "string"        true  false
add_or_replace_field "catalog_name"    "string"        true  false   # parent table name
add_or_replace_field "data_type"       "string"        true  false
add_or_replace_field "is_primary_key"  "boolean"       true  false
add_or_replace_field "is_foreign_key"  "boolean"       true  false
add_or_replace_field "is_nullable"     "boolean"       true  false

# ── TAG-specific ───────────────────────────────────────────────────────────────
add_or_replace_field "tag_color"       "string"        true  false


# ── SOURCE-specific ────────────────────────────────────────────────────────────
add_or_replace_field "source_type"     "string"        true  false   # postgres, mysql …
add_or_replace_field "source_status"   "string"        true  false   # running | failed | success

# ── OWNER-specific ─────────────────────────────────────────────────────────────
add_or_replace_field "owner_role"      "string"        true  false
add_or_replace_field "owner_email"     "string"        true  false

# ── Shared relational context (stored for display) ─────────────────────────────
add_or_replace_field "owner_id"        "string"        true  false
add_or_replace_field "owner_name"      "string"        true  false

# ── Multi-value association fields (tags / domains on catalogs) ────────────────
add_or_replace_field "tag_ids"         "string"        true  true
add_or_replace_field "tag_names"       "string"        true  true


# ── Timestamps ────────────────────────────────────────────────────────────────
add_or_replace_field "created_at"      "pdate"         true  false
add_or_replace_field "updated_at"      "pdate"         true  false

# ── Unified full-text search field ────────────────────────────────────────────
add_or_replace_field "search_text"     "text_general"  true  true

# ── Copy fields → search_text ─────────────────────────────────────────────────
for src in name display_name description full_name table_name schema_name \
           database_name data_type owner_name source_name tag_names  \
           group_name owner_email; do
  echo "Copy field: ${src} → search_text"
  add_copy_field "${src}" "search_text"
done

echo ""
echo " Solr schema configuration complete for core: ${CORE}"