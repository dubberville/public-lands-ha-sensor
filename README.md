![icon](https://github.com/user-attachments/assets/de5ad0b3-8f84-4b37-a003-0a3bd3b0b2b2)

# Public Lands
![Home Assistant](https://img.shields.io/badge/Home%20Assistant-compatible-blue)

> **This is a fork** of [anthonysecco/public-lands-ha-sensor](https://github.com/anthonysecco/public-lands-ha-sensor)
> by Anthony Secco, who wrote the original integration and everything it already did well.
> This fork adds a **nearby open public land** lookup: when you are *not* on public land, it tells
> you what is close, how far, in which direction, and gives you a one-tap navigation link.

This is a HACS Custom Component that queries ARCGIS [US Government Protected Area Data](https://services.arcgis.com/v01gqwM5QqNysAAi/ArcGIS/rest/services/Protection_Mechanism_Category_PADUS/FeatureServer/0) with your current GPS coordinates set in Home Assistant and will post back a response with details.

This sensor should provide information on almost any protected land in the United States including federal, state, county, and regional lands.  This can be useful when finding dispersed camping to quickly understand what land and jurisdiction you are within.

> An Internet connection is required for this integration to work.
>
> Only available for public lands in the United States.

This integration pairs nicely with [Geolocator](https://github.com/SmartyVan/hass-geolocator) by [SmartyVan](https://www.youtube.com/@SmartyVan) which provides geocoded address and timezone services.

⚠️ **Dispersed Camping  Disclaimer** ⚠️

Use your judgement when deciding where to setup a dispersed camp.  I am not responsible for the accuracy of the data or whether you run into problems at your chosen location.  Refer to the applicable government website for rules and regulations on dispersed camping for your chosen location.

With that out of the way, let's get started...

## Installation

[![Open your Home Assistant instance and open a repository inside the Home Assistant Community Store.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=dubberville&repository=public-lands-ha-sensor&category=integration)

> This integration is not yet available in the HACS default store.  Meanwhile, it will be added as a custom repository.

1. Click "Open HACS Repository" button above and install **Public Lands**
2. Restart Home Assistant
3. Navigate to Settings > Devices & Services
4. Click **Add Integration** at the bottom
5. Search for **Public Lands**

### Manual Installation

1. Download the source code of the [latest release](https://github.com/dubberville/public-lands-ha-sensor/releases).
2. Unzip the source code download.
3. Copy **public_lands** from the **custom_components** directory you just downloaded to your Home Assistant **custom_components** directory:
   ```
   config/custom_components/public_lands/
   ```
4. Restart Home Assistant.

## Usage

Upon restart, it will automatically create the sensors and button.  No configuration needed.  No data will be found in those sensors until it is triggered.  Please see the following section for details on that.

###Trigger Methods

#### Press the Button
This is simple.  If you want to know your USPL status immediately based on Home Assistant's current coordinate, press the button.

![image](https://github.com/user-attachments/assets/57a87b6e-a57f-4bb3-8e7f-d66b9b1e4b7e)

#### Create Automation

##### Upon GPS Update
Here's an example automation that will refresh USPL data when the zone.home is updated.  It will update at 10 minute intervals when the GPS coordinates are changing.

```yaml
alias: "USPL: Update via Button"
description: "Presses the Refresh USPL button when zone.home changes, throttled to once every 10 minutes."
trigger:
  - platform: state
    entity_id: zone.home
condition:
  - condition: template
    value_template: >
      {{ (as_timestamp(now()) - as_timestamp(this.last_triggered | default(0))) > 600 }}
action:
  - service: button.press
    target:
      entity_id: button.refresh_uspl
mode: single
```

##### Upon Parking
If you use a binary sensor to track when RV is moving / not moving, I suggest triggering a button press when transitioning from moving to not moving state.  This will capture the GPS coordinates at the time the vehicle stops and not the last update interval.  This is relevant when stopping to validate the jurisdiction of a campsite.

### Sensors
The following sensors will be created upon installation.

| Sensor | Description |
|--------|-------------|
| Unit Name | This is the high level known name "Yosemite National Park" or "Alabama Hills National Scenic Area." |
| Designation | Wilderness Area, National Park etc. |
| Management Name | National Park Service, Bureau of Land Management etc. |
| Management Type | State, Federal, Regional etc. |
| Public Access | Open to the public, Restricted (permit needed), Closed Access (military base). |
| API Status | 'On' if last refresh was successful.  'Off' if last refresh failed. |
| Last Successful Refresh | Timestamp of last referesh |
| Nearest Open Land | Closest open public land when you are *not* on public land. See below. |
| Nearby Count | How many matching units are within the search radius. |

These sensors will not populate with data unless the USPL Refresh Button is pressed.  You may see 'unknown' after Home Assistant starts until the next button press.

#### No Internet Connection Scenario
In the event there's no connectivity, the sensors will retain their old values.  API status will be set to 'off'.  Once the condition clears, API status will be set to 'on' and all sensors will refresh.

### Buttons
The integration will create one button

| Button | Description |
|--------|-------------|
| Refresh USPL | Pressing this button will call for the API with Home Assistant's current coordinates. |

The button can be exposed to the UI for manual trigger or via automations previously mentioned.

## Nearby Open Public Land

When the point lookup comes back as `Non-Protected Area`, the same button press runs a
second query for open public land **around** you. When you are already on public land the
second query is skipped entirely, and any existing markers are cleared.

There is still only one button and no polling. Your existing automation does not change.

### `sensor.uspl_nearest_open_land`

State is the name of the closest match, or `None within range`.

| Attribute | Description |
|-----------|-------------|
| `distance_miles` | Straight-line distance to the closest point of that unit. |
| `bearing_degrees` / `bearing_compass` | Direction from you, e.g. `293` / `WNW`. |
| `manager` / `management_type` / `designation` / `public_access` | Same PAD-US fields as the main sensors. |
| `latitude` / `longitude` | The closest point on that unit, not its centre. |
| `google_maps_url` / `apple_maps_url` | Turn-by-turn navigation to that point. |
| `result_count` | Matches found within the radius. |
| `search_radius_miles` | Radius used for this lookup. |
| `nearby_status` | `ok`, `stale` (last nearby query failed, values are from before), or `on_public_land`. |

### `sensor.uspl_nearby_count`

Number of matching units within the radius.

### Map markers

Each match becomes a `geo_location` entity, so they show up on a normal map card with no
dashboard work. They are recreated on every refresh and removed when you are back on
public land.

```yaml
type: map
entities:
  - zone.home
geo_location_sources:
  - public_lands
auto_fit: true
hours_to_show: 0
```

`hours_to_show: 0` keeps the map from drawing location history trails.

A tap-to-navigate card for the nearest match. The entities card cannot template a link,
so use a markdown card for the navigation link itself:

```yaml
type: markdown
content: >-
  {% set s = 'sensor.uspl_nearest_open_land' %}
  {% if states(s) not in ['None within range', 'unknown', 'unavailable'] %}
  ### {{ states(s) }}

  **{{ state_attr(s, 'distance_miles') }} mi {{ state_attr(s, 'bearing_compass') }}**
  &middot; {{ state_attr(s, 'manager') }}

  {{ state_attr(s, 'designation') }}

  [Navigate]({{ state_attr(s, 'apple_maps_url') }})
  &middot; [Google]({{ state_attr(s, 'google_maps_url') }})
  {% else %}
  No open public land within {{ state_attr(s, 'search_radius_miles') }} mi.
  {% endif %}
```

## Options

Settings > Devices & Services > Public Lands > **Configure**. Changes take effect on the
next button press; no restart needed.

| Option | Default | Notes |
|--------|---------|-------|
| Search radius | 25 mi | 5 to 100. Larger radii return more data and take longer. |
| Land managers | BLM, USFS | Groups: BLM, USFS, NPS, FWS, State, County/Regional, Other Federal. |
| Open access only | on | Restricts to land marked open to the public (`Pub_Access = OA`). |
| Maximum map markers | 10 | How many `geo_location` entities to create. |

BLM and Forest Service are the defaults because they are where dispersed camping is
usually allowed. NPS and state parks will mostly *not* let you disperse camp, so adding
them is useful for knowing what is around you, not for finding a site.

> **What this can and cannot tell you.** PAD-US knows who manages a piece of land and
> whether it is open to the public. It does **not** know whether dispersed camping is
> allowed at a given spot, whether there is a road, or whether that road is passable.
> Treat a nearby result as "worth looking into," not as permission. The dispersed camping
> disclaimer above applies to every one of these results.

### Testing from the command line

`scripts/nearby_test.py` runs the same query and the same geometry code the integration
uses, without needing Home Assistant. Useful for sanity checking before a restart.

```
python3 scripts/nearby_test.py 36.15 -115.15 25
python3 scripts/nearby_test.py 31.22 -85.39 100 --managers BLM,USFS,State
```

### Dashboard Visability Recommendations

If you want to hide USPL sensors when they're unavailable (such as no Internet connectivity), use the API status and conditional visability in your dashboard.

If you want to hide USPL sensors when on private land, hide when 'Unit Name' is 'Non-Protected Area'.

### Example Data

**Public Land**

![image](https://github.com/user-attachments/assets/00ed28f7-26b3-4228-8489-aa490f7b0807)

![image](https://github.com/user-attachments/assets/55b51e88-e30e-4279-a5f0-184be36588fa)

![image](https://github.com/user-attachments/assets/c7ebddaa-8812-429f-bf1b-c62fa6d7a434)

![image](https://github.com/user-attachments/assets/3e7802b6-4a40-4656-91f9-467b24d82469)

**Non-Public Land**

![image](https://github.com/user-attachments/assets/d542a6f6-8fcd-4da2-8b8c-27b513d92afc)

## Notes

- **Connectivity** - Internet is required at the time of the button press.
- **Polling** - The integration does not automatically poll.  It leaves this task to the user to configure either manually or via automation.
- **Frequency** - Please limit your automated refresh period to no less than **10 minutes** while in motion.
- **GPS Accuracy** - The GPS coordinateds are limited to four decimal points (-118.1222,36.5597).  This limits the accuracy to 15 meters.
- **Data Accuracy** - The API data is refreshed annually in June by USGS (United States Geological Survey).
- **Nearby distances** - Distance is straight-line to the nearest point on the unit boundary, not
  driving distance. The boundary is simplified server-side, so treat the figure as accurate to about
  a tenth of a mile. There may be no legal road to that point.
- **Dependencies** - None. The distance maths is plain Python, so there is nothing to compile and
  nothing to break on a Home Assistant upgrade.

## Contributions

All credit for the original integration goes to [Anthony Secco](https://github.com/anthonysecco).
This fork only adds the nearby lookup on top of his work, and keeps the original MIT license.

Thanks to Smarty Van for [Geolocator](https://github.com/SmartyVan/hass-geolocator) which served as a starting point for this integration.

Open issues, suggest improvements, or contribute pull requests directly here on GitHub.

## License

This project is licensed under the MIT License. For more details, see the LICENSE file.&#x20;
