DOMAIN = "public_lands"

# PAD-US Public Access feature layer (polygons, EPSG:4326)
ARCGIS_URL = (
    "https://services.arcgis.com/v01gqwM5QqNysAAi/arcgis/rest/services/"
    "PADUS_Public_Access/FeatureServer/0/query"
)

OUT_FIELDS = "Unit_Nm,Pub_Access,MngTp_Desc,MngNm_Desc,DesTp_Desc"

# Unit_Nm value the point query returns when the location is not on PAD-US land.
NON_PADUS = "Non-PAD-US Area"

# Options keys
CONF_RADIUS = "search_radius_miles"
CONF_MANAGERS = "managers"
CONF_OPEN_ONLY = "open_access_only"
CONF_MAX_RESULTS = "max_results"

DEFAULT_RADIUS = 25
MIN_RADIUS = 5
MAX_RADIUS = 100
DEFAULT_MANAGERS = ["BLM", "USFS"]
DEFAULT_OPEN_ONLY = True
DEFAULT_MAX_RESULTS = 10

# This layer has no coded manager fields -- only the *_Desc text fields -- so the
# where clause matches on full description strings. Values verified against the
# layer's distinct MngNm_Desc list.
MANAGER_GROUPS = {
    "BLM": ["Bureau of Land Management"],
    "USFS": ["Forest Service"],
    "NPS": ["National Park Service"],
    "FWS": ["U.S. Fish and Wildlife Service"],
    "State": [
        "State Department of Conservation",
        "State Department of Land",
        "State Department of Natural Resources",
        "State Fish and Wildlife",
        "State Land Board",
        "State Park and Recreation",
        "Other or Unknown State Land",
    ],
    "County/Regional": [
        "City Land",
        "County Land",
        "Regional Agency Land",
        "Regional Water Districts",
        "Other or Unknown Local Government",
    ],
    "Other Federal": [
        "Agricultural Research Service",
        "Army Corps of Engineers",
        "Bureau of Reclamation",
        "Department of Defense",
        "Department of Energy",
        "National Oceanic and Atmospheric Administration",
        "Natural Resources Conservation Service",
        "Tennessee Valley Authority",
        "Other or Unknown Federal Land",
    ],
}
