#!/usr/bin/env python3
# -*- encoding: utf-8 -*-
# vim: tabstop=2 shiftwidth=2 softtabstop=2 expandtab

import os
import json
import googlemaps
from google.adk.tools import LongRunningFunctionTool

def find_restaurants_in_google_maps(query: str) -> str:
  """
  Finds restaurants based on a user's query, which should include the food and location.

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

find_restaurants = LongRunningFunctionTool(func=find_restaurants_in_google_maps)
