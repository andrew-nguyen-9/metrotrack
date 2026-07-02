{# Normalize a GTFS route_type into MetroTrack's mode vocabulary. #}
{# GTFS route_type: 0 tram/light-rail, 1 subway/metro, 2 rail (commuter), #}
{# 3 bus, 5 cable tram, 7 funicular, 11 trolleybus, 12 monorail. #}
{# CTA 'L' = 1 → rail; Metra = 2 → commuter-rail; CTA/Pace bus = 3 → bus. #}
{% macro route_mode(route_type_col) -%}
case
    when {{ route_type_col }} in (0, 1, 5, 7, 12) then 'rail'
    when {{ route_type_col }} = 2 then 'commuter-rail'
    when {{ route_type_col }} in (3, 11) then 'bus'
    else 'other'
end
{%- endmacro %}
