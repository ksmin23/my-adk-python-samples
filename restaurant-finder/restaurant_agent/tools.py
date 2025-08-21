#!/usr/bin/env python3
# -*- encoding: utf-8 -*-
# vim: tabstop=2 shiftwidth=2 softtabstop=2 expandtab

import os
import json
import googlemaps
from google.adk.tools import LongRunningFunctionTool
from google.maps import places_v1

def find_restaurants_in_google_maps(query: str) -> str:
  """
  Finds restaurants based on a user's query using the legacy Places API.

  Args:
    query: A search query string, e.g., "김치찌개 near 서울 강남역" or "아보카도 샐러드 in 판교".

  Returns:
    A JSON string containing a list of found restaurants or a message if none were found.
  """
  api_key = os.getenv("GOOGLE_MAPS_API_KEY")
  if not api_key:
    return json.dumps({"error": "Google Maps API key is not configured."})

  gmaps = googlemaps.Client(key=api_key)

  try:
    # Use places API (Text Search)
    places_result = gmaps.places(query=query, language='ko')

    if places_result and places_result.get('status') == 'OK':
      restaurants = []
      for place in places_result.get('results', []):
        restaurants.append({
          "name": place.get('name'),
          "address": place.get('formatted_address'),
          "rating": place.get('rating', 'N/A')
        })
      if restaurants:
        return json.dumps(restaurants)

    return json.dumps({"message": "No restaurants found matching your criteria."})

  except Exception as e:
    # In a real application, you would want to log this error.
    print(f"An error occurred: {e}")
    return json.dumps({"error": "An error occurred while searching for restaurants."})

def find_restaurants_in_google_maps_v2(query: str, language_code: str = "ko", region_code: str = "KR", max_results: int = 5) -> str:
  """
  Finds restaurants using the Places API (New) based on a user's query.

  Args:
    query: The user's search query (e.g., "restaurants with outdoor seating").
    language_code: The language of the results.
    region_code: The region to search in.
    max_results: The maximum number of results to return.

  Returns:
    A JSON string containing a list of found restaurants or a message if none were found.
  """
  try:
    client = places_v1.PlacesClient()

    request = places_v1.SearchTextRequest(
        text_query=query,
        language_code=language_code,
        region_code=region_code,
        max_result_count=max_results,
    )

    # Define which fields to return for efficiency
    field_mask = "places.rating,places.formattedAddress,places.displayName,places.googleMapsUri"

    response = client.search_text(request=request, metadata=[("x-goog-fieldmask", field_mask)])

    restaurants = []
    for place in response.places:
      restaurants.append({
        "name": place.display_name.text,
        "address": place.formatted_address,
        "rating": place.rating if place.rating else 'N/A',
        "map_uri": place.google_maps_uri
      })

    if restaurants:
      return json.dumps(restaurants)
    else:
      return json.dumps({"message": "No restaurants found matching your criteria."})

  except Exception as e:
    print(f"An error occurred with Places API v2: {e}")
    return json.dumps({"error": "An error occurred while searching for restaurants."})


# find_restaurants = LongRunningFunctionTool(func=find_restaurants_in_google_maps)
find_restaurants = LongRunningFunctionTool(func=find_restaurants_in_google_maps_v2)