# server.py (v12 - Resilient Geocoding)

import sqlite3
from flask import Flask, jsonify, send_from_directory
from datetime import datetime
from flask_cors import CORS
import re
from geopy.geocoders import Nominatim
from geopy.extra.rate_limiter import RateLimiter

DATABASE_FILE = 'fleet.db'

# Initialize the geocoder
geolocator = Nominatim(user_agent="fleet_tracker_app/1.0")
geocode = RateLimiter(geolocator.geocode, min_delay_seconds=1)

# This hardcoded data is now primarily for static info and a fallback for coordinates
FALLBACK_FLEET_DATA = {
    "lastUpdated": "2025-06-29",
    "ships": [
        { "name": "USS Gerald R. Ford", "hull": "CVN-78", "class": "Aircraft Carrier", "country": "USA", "group": "Gerald R. Ford CSG", "homeport": "Norfolk, Va.", "status": "Operating in the Eastern Mediterranean.", "coordinates": [26.0, 35.0], "image": "images/cvn78.jpg", "description": "The lead ship of the Gerald R. Ford class of supercarriers. She is the most technologically advanced aircraft carrier ever built, featuring an Electromagnetic Aircraft Launch System (EMALS) and Advanced Arresting Gear (AAG).", "region": "Mediterranean Sea", "locationReported": "2025-06-28", "commissionedYear": 2017, "length_ft": 1106, "beam_ft": 256, "draft_ft": 39, "speed_kn": 30, "complement": 4539, "tonnage": 100000, "history": "First-in-class carrier, represents the future of naval aviation.", "armament": ["ESSM", "RAM", "CIWS"] },
        { "name": "USS Normandy", "hull": "CG-60", "class": "Cruiser", "country": "USA", "group": "Gerald R. Ford CSG", "homeport": "Norfolk, Va.", "status": "Providing air defense in the Eastern Mediterranean.", "coordinates": [26.5, 34.5], "image": "images/cg60.jpg", "description": "A Ticonderoga-class guided-missile cruiser equipped with the Aegis Combat System. Her primary missions are to conduct anti-air warfare, anti-submarine warfare, and anti-surface warfare in support of the carrier strike group.", "region": "Mediterranean Sea", "locationReported": "2025-06-28", "commissionedYear": 1989, "length_ft": 567, "beam_ft": 55, "draft_ft": 34, "speed_kn": 32.5, "complement": 330, "tonnage": 9600, "history": "Extensive service history including operations in the Persian Gulf and Mediterranean.", "armament": ["Mk 41 VLS", "Harpoon Missiles", "5-inch gun", "CIWS"] },
        { "name": "USS Ramage", "hull": "DDG-61", "class": "Destroyer", "country": "USA", "group": "Gerald R. Ford CSG", "homeport": "Norfolk, Va.", "status": "Escort duty in the Mediterranean.", "coordinates": [25.5, 34.0], "image": "images/ddg61.jpg", "description": "An Arleigh Burke-class destroyer capable of fighting air, surface, and subsurface battles simultaneously. Named for Vice Admiral Lawson P. Ramage, a notable submarine commander.", "region": "Mediterranean Sea", "locationReported": "2025-06-27", "commissionedYear": 1995, "length_ft": 505, "beam_ft": 66, "draft_ft": 31, "speed_kn": 30, "complement": 280, "tonnage": 8315, "history": "Multiple deployments to the Mediterranean and Middle East in support of US and NATO operations.", "armament": ["Mk 41 VLS", "5-inch gun", "CIWS", "Torpedoes"] },
        { "name": "USS Harry S. Truman", "hull": "CVN-75", "class": "Aircraft Carrier", "country": "USA", "group": "Harry S. Truman CSG", "homeport": "Norfolk, Va.", "status": "Conducting flight operations in the Arabian Sea.", "coordinates": [62.0, 20.0], "image": "images/cvn75.jpg", "description": "The eighth Nimitz-class aircraft carrier, named after the 33rd President of the United States. She is a nuclear-powered supercarrier capable of projecting power and maintaining presence worldwide.", "region": "Arabian Sea", "locationReported": "2025-06-27", "commissionedYear": 1998, "length_ft": 1092, "beam_ft": 252, "draft_ft": 37, "speed_kn": 30, "complement": 5680, "tonnage": 101400, "history": "Key participant in Operation Iraqi Freedom and Operation Enduring Freedom.", "armament": ["ESSM", "RAM", "CIWS"] },
        { "name": "USS San Jacinto", "hull": "CG-56", "class": "Cruiser", "country": "USA", "group": "Harry S. Truman CSG", "homeport": "Norfolk, Va.", "status": "Air defense command in the Arabian Sea.", "coordinates": [62.5, 20.5], "image": "images/cg56.jpg", "description": "A Ticonderoga-class guided-missile cruiser. She participated in the opening strikes of Operation Desert Storm and has a long history of deployments.", "region": "Arabian Sea", "locationReported": "2025-06-27", "commissionedYear": 1988, "length_ft": 567, "beam_ft": 55, "draft_ft": 34, "speed_kn": 32.5, "complement": 330, "tonnage": 9600, "history": "Fired the first Tomahawk cruise missiles in the opening phase of Operation Desert Storm.", "armament": ["Mk 41 VLS", "Harpoon Missiles", "5-inch gun", "CIWS"] },
        { "name": "USS Cole", "hull": "DDG-67", "class": "Destroyer", "country": "USA", "group": "Harry S. Truman CSG", "homeport": "Norfolk, Va.", "status": "Maritime security operations in the Gulf of Oman.", "coordinates": [58.0, 24.0], "image": "images/ddg67.jpg", "description": "An Arleigh Burke-class destroyer famously targeted in a terrorist attack in 2000. After extensive repairs, she returned to the fleet and remains a symbol of American resolve.", "region": "Arabian Sea", "locationReported": "2025-06-26", "commissionedYear": 1996, "length_ft": 505, "beam_ft": 66, "draft_ft": 31, "speed_kn": 30, "complement": 280, "tonnage": 8400, "history": "Survived a terrorist bombing in Aden, Yemen, in 2000, and returned to full operational status.", "armament": ["Mk 41 VLS", "5-inch gun", "CIWS", "Torpedoes"] },
        { "name": "USS Theodore Roosevelt", "hull": "CVN-71", "class": "Aircraft Carrier", "country": "USA", "group": "Theodore Roosevelt CSG", "homeport": "San Diego, Calif.", "status": "Operating in the South China Sea.", "coordinates": [115.0, 14.0], "image": "images/cvn71.jpg", "description": "The fourth Nimitz-class aircraft carrier, nicknamed 'the Big Stick'. She has a storied history, including service in Operation Desert Storm and Operation Iraqi Freedom.", "region": "South China Sea", "locationReported": "2025-06-28", "commissionedYear": 1986, "length_ft": 1092, "beam_ft": 252, "draft_ft": 37, "speed_kn": 30, "complement": 5680, "tonnage": 104600, "history": "Decades of service including combat operations in the Persian Gulf and against ISIS.", "armament": ["ESSM", "RAM", "CIWS"] },
        { "name": "USS Bunker Hill", "hull": "CG-52", "class": "Cruiser", "country": "USA", "group": "Theodore Roosevelt CSG", "homeport": "San Diego, Calif.", "status": "Coordinating air defense in the South China Sea.", "coordinates": [115.5, 14.5], "image": "images/cg52.jpg", "description": "A Ticonderoga-class guided-missile cruiser, notable for being one of the first ships in the class equipped with the advanced Mark 41 Vertical Launching System (VLS).", "region": "South China Sea", "locationReported": "2025-06-28", "commissionedYear": 1986, "length_ft": 567, "beam_ft": 55, "draft_ft": 34, "speed_kn": 32.5, "complement": 330, "tonnage": 9600, "history": "One of the first Aegis cruisers, setting the standard for modern naval air defense.", "armament": ["Mk 41 VLS", "Harpoon Missiles", "5-inch gun", "CIWS"] },
        { "name": "USS Russell", "hull": "DDG-59", "class": "Destroyer", "country": "USA", "group": "Theodore Roosevelt CSG", "homeport": "San Diego, Calif.", "status": "Freedom of navigation operations.", "coordinates": [116.0, 13.5], "image": "images/ddg59.jpg", "description": "An Arleigh Burke-class destroyer named for Rear Admiral John Henry Russell and his son, Major General John Henry Russell, Jr. She is a versatile multi-mission warship.", "region": "South China Sea", "locationReported": "2025-06-27", "commissionedYear": 1995, "length_ft": 505, "beam_ft": 66, "draft_ft": 31, "speed_kn": 30, "complement": 280, "tonnage": 8315, "history": "Active in the Pacific fleet, participating in numerous international exercises.", "armament": ["Mk 41 VLS", "5-inch gun", "CIWS", "Torpedoes"] },
        { "name": "USS America", "hull": "LHA-6", "class": "Amphibious Assault Ship", "country": "USA", "group": "America ARG", "homeport": "Sasebo, Japan", "status": "Conducting amphibious exercises in the Philippine Sea.", "coordinates": [135.0, 18.0], "image": "images/lha6.jpg", "description": "The lead ship of the America-class amphibious assault ships. Optimized for aviation, she can carry a squadron of F-35B Lightning II stealth fighters, acting as a small aircraft carrier or supporting Marine Corps amphibious operations.", "region": "Philippine Sea", "locationReported": "2025-06-26", "commissionedYear": 2014, "length_ft": 844, "beam_ft": 106, "draft_ft": 26, "speed_kn": 22, "complement": 1204, "tonnage": 45000, "history": "First of her class, designed to maximize the capabilities of the F-35B and MV-22 Osprey.", "armament": ["ESSM", "RAM", "CIWS", ".50-cal machine guns"] },
        { "name": "USS Green Bay", "hull": "LPD-20", "class": "Amphibious Transport Dock", "country": "USA", "group": "America ARG", "homeport": "Sasebo, Japan", "status": "Supporting Marine operations in the Philippine Sea.", "coordinates": [135.5, 18.5], "image": "images/lpd20.jpg", "description": "A San Antonio-class amphibious transport dock. These ships are used to transport and land Marines, their equipment, and supplies by embarked air cushion or conventional landing craft and amphibious assault vehicles.", "region": "Philippine Sea", "locationReported": "2025-06-26", "commissionedYear": 2009, "length_ft": 684, "beam_ft": 105, "draft_ft": 23, "speed_kn": 22, "complement": 360, "tonnage": 25000, "history": "Forward-deployed to Japan as a key component of the 7th Fleet's amphibious forces.", "armament": ["Rolling Airframe Missiles", "30mm Bushmaster cannons"] },
        { "name": "USS Iwo Jima", "hull": "LHD-7", "class": "Amphibious Assault Ship", "country": "USA", "group": "Iwo Jima ARG", "homeport": "Norfolk, Va.", "status": "Underway for training exercises in the North Atlantic.", "coordinates": [-40.0, 50.0], "image": "images/lhd7.jpg", "description": "A Wasp-class amphibious assault ship designed to embark, deploy, and land elements of a Marine Landing Force in amphibious operations by helicopter, landing craft, and amphibious vehicles.", "region": "North Atlantic", "locationReported": "2025-06-22", "commissionedYear": 2001, "length_ft": 843, "beam_ft": 104, "draft_ft": 27, "speed_kn": 22, "complement": 1208, "tonnage": 40500, "history": "Deployed for humanitarian relief missions, including after Hurricane Katrina, and combat support operations.", "armament": ["ESSM", "RAM", "CIWS", ".50-cal machine guns"] },
        { "name": "USS Arleigh Burke", "hull": "DDG-51", "class": "Destroyer", "country": "USA", "group": "Independent Deployer", "homeport": "Rota, Spain", "status": "Patrolling the Black Sea.", "coordinates": [35.0, 44.0], "image": "images/ddg51.jpg", "description": "The lead ship of the Arleigh Burke-class of guided-missile destroyers. These ships are multi-mission surface combatants capable of conducting Anti-Air Warfare (AAW), Anti-Submarine Warfare (ASW), and Anti-Surface Warfare (ASuW) simultaneously.", "region": "Black Sea", "locationReported": "2025-06-24", "commissionedYear": 1991, "length_ft": 505, "beam_ft": 66, "draft_ft": 31, "speed_kn": 30, "complement": 280, "tonnage": 8315, "history": "The first of the most successful and longest-serving class of destroyers in the US Navy.", "armament": ["Mk 41 VLS", "5-inch gun", "CIWS", "Torpedoes"] },
        { "name": "USS Forrest Sherman", "hull": "DDG-98", "class": "Destroyer", "country": "USA", "group": "Independent Deployer", "homeport": "Norfolk, Va.", "status": "Transiting the Red Sea.", "coordinates": [39.0, 20.0], "image": "images/ddg98.jpg", "description": "An Arleigh Burke-class destroyer, part of the improved 'Flight IIA' design which adds a helicopter hangar. Named after Admiral Forrest Percival Sherman, the youngest man to serve as Chief of Naval Operations.", "region": "Red Sea", "locationReported": "2025-06-25", "commissionedYear": 2006, "length_ft": 509, "beam_ft": 66, "draft_ft": 31, "speed_kn": 30, "complement": 320, "tonnage": 9200, "history": "Has participated in numerous anti-piracy and maritime security operations.", "armament": ["Mk 41 VLS", "5-inch gun", "CIWS", "Torpedoes"] },
        { "name": "USS The Sullivans", "hull": "DDG-68", "class": "Destroyer", "country": "USA", "group": "Independent Deployer", "homeport": "Mayport, Fla.", "status": "Counter-drug operations in the Caribbean Sea.", "coordinates": [-75.0, 15.0], "image": "images/ddg68.jpg", "description": "An Arleigh Burke-class destroyer named in honor of the five Sullivan brothers who were killed in action when their ship, USS Juneau, was sunk in World War II. Its motto is 'We Stick Together.'", "region": "Caribbean Sea", "locationReported": "2025-06-23", "commissionedYear": 1997, "length_ft": 505, "beam_ft": 66, "draft_ft": 31, "speed_kn": 30, "complement": 280, "tonnage": 8400, "history": "Named to honor the memory of the five Sullivan brothers who died on the USS Juneau during WWII.", "armament": ["Mk 41 VLS", "5-inch gun", "CIWS", "Torpedoes"] },
        { "name": "USS Virginia", "hull": "SSN-774", "class": "Submarine", "country": "USA", "group": "Independent Deployer", "homeport": "Groton, Conn.", "status": "On patrol in the Barents Sea.", "coordinates": [35.0, 73.0], "image": "images/ssn774.jpg", "description": "The lead boat of the Virginia-class of nuclear-powered cruise missile fast-attack submarines. These submarines are designed for a broad spectrum of open-ocean and littoral missions.", "region": "Barents Sea", "locationReported": "2025-06-20", "commissionedYear": 2004, "length_ft": 377, "beam_ft": 34, "draft_ft": 32, "speed_kn": 25, "complement": 135, "tonnage": 7800, "history": "The first of a new class of attack submarines designed for the post-Cold War era.", "armament": ["Tomahawk Missiles", "Mk 48 Torpedoes"] },
        { "name": "USS Ohio", "hull": "SSGN-726", "class": "Submarine", "country": "USA", "group": "Independent Deployer", "homeport": "Kings Bay, Ga.", "status": "On station in the Indian Ocean.", "coordinates": [80.0, 0.0], "image": "images/ssgn726.jpg", "description": "Originally an Ohio-class ballistic missile submarine (SSBN), USS Ohio was converted to a guided-missile submarine (SSGN). She is capable of carrying up to 154 Tomahawk cruise missiles and supporting special operations forces.", "region": "Indian Ocean", "locationReported": "2025-06-15", "commissionedYear": 1981, "length_ft": 560, "beam_ft": 42, "draft_ft": 38, "speed_kn": 20, "complement": 155, "tonnage": 18750, "history": "Lead ship of her class, converted from a ballistic missile role to a conventional strike and SOF platform.", "armament": ["154 Tomahawk Missiles", "Mk 48 Torpedoes"] },
        { "name": "USS Mount Whitney", "hull": "LCC-20", "class": "Command Ship", "country": "USA", "group": "U.S. 6th Fleet", "homeport": "Gaeta, Italy", "status": "Flagship of the U.S. 6th Fleet, in the Ionian Sea.", "coordinates": [19.0, 38.0], "image": "images/lcc20.jpg", "description": "One of two Blue Ridge-class amphibious command ships of the United States Navy, and is the flagship and command ship of the United States Sixth Fleet.", "region": "Mediterranean Sea", "locationReported": "2025-06-29", "commissionedYear": 1971, "length_ft": 620, "beam_ft": 108, "draft_ft": 29, "speed_kn": 23, "complement": 325, "tonnage": 18400, "history": "The most sophisticated command and control ship ever built, serving as the 6th Fleet flagship for decades.", "armament": ["CIWS", ".50-cal machine guns", "25mm Bushmaster cannons"] },
        { "name": "USS Miguel Monsoor", "hull": "DDG-1001", "class": "Destroyer", "country": "USA", "group": "Independent Deployer", "homeport": "San Diego, CA", "status": "Underway in the Eastern Pacific for exercises.", "coordinates": [-125.0, 34.0], "image": "images/ddg1001.jpg", "description": "The second ship of the Zumwalt class of guided-missile destroyers, featuring a unique stealth tumblehome hull design.", "region": "Eastern Pacific", "locationReported": "2025-06-28", "commissionedYear": 2019, "length_ft": 610, "beam_ft": 80, "draft_ft": 27, "speed_kn": 30, "complement": 175, "tonnage": 15995, "history": "A technologically advanced destroyer designed for littoral operations and land attack.", "armament": ["Mk 57 PVLS", "Advanced Gun System (AGS)"] },
        { "name": "USS Hershel 'Woody' Williams", "hull": "ESB-4", "class": "Expeditionary Sea Base", "country": "USA", "group": "Independent Deployer", "homeport": "Souda Bay, Greece", "status": "Operating off the coast of West Africa.", "coordinates": [-5.0, 5.0], "image": "images/esb4.jpg", "description": "An Expeditionary Sea Base (ESB) ship, which acts as a mobile sea base to support a variety of missions, including counter-piracy operations, maritime security, and humanitarian aid.", "region": "Atlantic Ocean", "locationReported": "2025-06-18", "commissionedYear": 2018, "length_ft": 785, "beam_ft": 164, "draft_ft": 39, "speed_kn": 15, "complement": 100, "tonnage": 90000, "history": "Named in honor of Hershel W. 'Woody' Williams, a Marine awarded the Medal of Honor for his actions at the Battle of Iwo Jima.", "armament": ["Support for helicopters", ".50-cal machine guns"] },
        { "name": "USNS John Lenthall", "hull": "T-AO-189", "class": "Replenishment Oiler", "country": "USA", "group": "Support Vessel", "homeport": "N/A", "status": "Supporting fleet operations in the Atlantic.", "coordinates": [-30.0, 30.0], "image": "images/tao189.jpg", "description": "A Henry J. Kaiser-class underway replenishment oiler operated by the Military Sealift Command to provide fuel, food, and other supplies to US Navy ships at sea, allowing the fleet to remain on station for extended periods.", "region": "Atlantic Ocean", "locationReported": "2025-06-29", "commissionedYear": 1987, "length_ft": 677, "beam_ft": 97, "draft_ft": 35, "speed_kn": 20, "complement": 89, "tonnage": 40224, "history": "A vital logistical asset for the Navy, ensuring combatant ships can remain at sea without returning to port.", "armament": ["N/A"] },
        { "name": "HMS Queen Elizabeth", "hull": "R08", "class": "Aircraft Carrier", "country": "UK", "group": "UK Carrier Strike Group", "homeport": "HMNB Portsmouth", "status": "On joint exercises in the North Sea.", "coordinates": [4.0, 58.0], "image": "images/r08.jpg", "description": "The lead ship of the Queen Elizabeth class of aircraft carriers, the largest warships ever built for the Royal Navy.", "region": "North Sea", "locationReported": "2025-06-28", "commissionedYear": 2017, "length_ft": 920, "beam_ft": 240, "draft_ft": 36, "speed_kn": 25, "complement": 679, "tonnage": 65000, "history": "The first of a new generation of British carriers, designed to operate the F-35B Lightning II.", "armament": ["CIWS", "30mm DS30M guns"] },
        { "name": "FS Charles de Gaulle", "hull": "R91", "class": "Aircraft Carrier", "country": "France", "group": "Charles de Gaulle CSG", "homeport": "Toulon, France", "status": "Underway in the Western Mediterranean.", "coordinates": [5.0, 41.0], "image": "images/r91.jpg", "description": "The flagship of the French Navy (Marine Nationale). The only nuclear-powered carrier completed outside of the United States Navy.", "region": "Mediterranean Sea", "locationReported": "2025-06-27", "commissionedYear": 2001, "length_ft": 858, "beam_ft": 211, "draft_ft": 31, "speed_kn": 27, "complement": 1950, "tonnage": 42500, "history": "Western Europe's only nuclear-powered carrier, flagship of the French Navy.", "armament": ["Aster 15 missiles", "Mistral missiles", "CIWS"] },
        { "name": "JS Izumo", "hull": "DDH-183", "class": "Helicopter Destroyer", "country": "Japan", "group": "JMSDF Escort Flotilla", "homeport": "Yokosuka, Japan", "status": "On patrol in the East China Sea.", "coordinates": [125.0, 30.0], "image": "images/ddh183.jpg", "description": "The lead ship in the Izumo class of helicopter destroyers of the Japan Maritime Self-Defense Force. Currently being converted to operate F-35B aircraft.", "region": "East China Sea", "locationReported": "2025-06-29", "commissionedYear": 2015, "length_ft": 814, "beam_ft": 125, "draft_ft": 24, "speed_kn": 30, "complement": 470, "tonnage": 27000, "history": "Largest Japanese surface combatant since WWII, currently being modified into a light aircraft carrier.", "armament": ["CIWS", "SeaRAM"] },
        { "name": "HMAS Sydney", "hull": "DDG 42", "class": "Destroyer", "country": "Australia", "group": "Independent Deployer", "homeport": "Sydney, Australia", "status": "Participating in RIMPAC exercises off Hawaii.", "coordinates": [-157.0, 21.0], "image": "images/ddg42.jpg", "description": "A Hobart-class guided-missile destroyer of the Royal Australian Navy, based on the Spanish F100 design.", "region": "Central Pacific", "locationReported": "2025-06-25", "commissionedYear": 2020, "length_ft": 481, "beam_ft": 61, "draft_ft": 24, "speed_kn": 28, "complement": 180, "tonnage": 7000, "history": "One of the newest and most capable warships in the Royal Australian Navy.", "armament": ["Mk 41 VLS", "Harpoon Missiles", "5-inch gun"] },
        { "name": "USS Jason Dunham", "hull": "DDG-109", "class": "Destroyer", "country": "USA", "group": "Independent Deployer", "homeport": "Mayport, Fla.", "status": "Returning to homeport from Atlantic deployment.", "coordinates": [-78.0, 33.0], "image": "images/ddg109.jpg", "description": "An Arleigh Burke-class destroyer named for Corporal Jason Dunham, a US Marine who was posthumously awarded the Medal of Honor for his service in the Iraq War.", "region": "Atlantic Ocean", "locationReported": "2025-06-29", "commissionedYear": 2010, "length_ft": 509, "beam_ft": 66, "draft_ft": 31, "speed_kn": 30, "complement": 320, "tonnage": 9200, "history": "Named for Medal of Honor recipient Jason Dunham, the first Marine to receive the honor since the Vietnam War.", "armament": ["Mk 41 VLS", "5-inch gun", "CIWS", "Torpedoes"] },
        { "name": "USS Vicksburg", "hull": "CG-69", "class": "Cruiser", "country": "USA", "group": "Independent Deployer", "homeport": "Mayport, Fla.", "status": "Undergoing modernization.", "coordinates": [-81.4, 30.3], "image": "images/cg69.jpg", "description": "A Ticonderoga-class guided-missile cruiser currently undergoing extensive modernization to extend its service life and enhance its combat capabilities.", "region": "In Port", "locationReported": "2025-06-29", "commissionedYear": 1992, "length_ft": 567, "beam_ft": 55, "draft_ft": 34, "speed_kn": 32.5, "complement": 330, "tonnage": 9600, "history": "Has a notable service record, including deployments to the Mediterranean and Persian Gulf.", "armament": ["Mk 41 VLS", "Harpoon Missiles", "5-inch gun", "CIWS"] }
    ]
}

app = Flask(__name__)
CORS(app)

def get_db_connection():
    conn = sqlite3.connect(DATABASE_FILE)
    conn.row_factory = sqlite3.Row
    return conn

# --- FINAL, ROBUST GEOCODING FUNCTION ---
def get_coords_from_status(status_text):
    """
    Tries to extract a known location from status text and return coordinates.
    This version uses a flexible regex and a two-step query process for reliability.
    """
    # This single, flexible pattern finds a keyword and the location text that follows.
    # It stops at a period, the end of the line, or ", according" to avoid grabbing extra text.
    match = re.search(
        r'\b(in|at|near|off|arrived in|underway in|transiting|operating in|off the coast of)\s+(?:the\s)?(.+?)(?:\.|$|, according)',
        status_text,
        re.IGNORECASE
    )

    if not match:
        print(f"DEBUG: No location pattern matched in status: '{status_text}'")
        return None

    keyword = match.group(1).lower()
    location_name = match.group(2).strip()
    
    # Determine the primary query based on context
    primary_query = location_name
    is_port_keyword = keyword in ['in', 'at', 'arrived in']
    is_ocean_body = 'sea' in location_name.lower() or 'ocean' in location_name.lower() or 'gulf' in location_name.lower()
    
    # If the keyword suggests a port and the location isn't a large body of water, search for the port.
    if is_port_keyword and not is_ocean_body:
        primary_query = f"Port of {location_name}"
    
    try:
        print(f"Attempting to geocode with primary query: '{primary_query}'")
        location = geocode(primary_query, timeout=10)

        # If the primary query fails AND it was a port search, try again with just the location name.
        if not location and primary_query.startswith("Port of"):
            fallback_query = location_name
            print(f"Primary query failed. Trying fallback: '{fallback_query}'")
            location = geocode(fallback_query, timeout=10)

        if location:
            print(f"SUCCESS: Geocoded query to: ({location.latitude}, {location.longitude})")
            return [location.longitude, location.latitude]
        else:
            print(f"FAILED: All geocoding attempts for status '{status_text}' returned no result.")
            return None
    except Exception as e:
        print(f"ERROR: Geocoding for query '{primary_query}' failed with an error: {e}")
        return None

@app.route('/')
def serve_index():
    return send_from_directory('.', 'index.html')

@app.route('/images/<path:filename>')
def serve_images(filename):
    return send_from_directory('images', filename)

@app.route('/api/fleet')
def get_fleet_data():
    try:
        conn = get_db_connection()
        scraped_ships_rows = conn.execute("SELECT name, hull, class, status, locationReported FROM ships").fetchall()
        conn.close()

        if not scraped_ships_rows:
            print("Database is empty or could not be read. Serving fallback data.")
            return jsonify(FALLBACK_FLEET_DATA)

        master_data_copy = {
            "lastUpdated": datetime.now().strftime("%Y-%m-%d"),
            "ships": [dict(ship) for ship in FALLBACK_FLEET_DATA['ships']]
        }
        
        scraped_map = {ship['hull']: ship for ship in scraped_ships_rows}

        for ship in master_data_copy['ships']:
            if ship['hull'] in scraped_map:
                scraped_info = scraped_map[ship['hull']]
                ship['status'] = scraped_info['status']
                ship['locationReported'] = scraped_info['locationReported']
                ship['class'] = scraped_info['class']
                
                print(f"\nProcessing ship: {ship['name']}")
                new_coords = get_coords_from_status(ship['status'])
                if new_coords:
                    ship['coordinates'] = new_coords
                else:
                    print(f"Geocoding failed for status: \"{ship['status']}\". Using static coordinates.")
        
        print(f"\nServing {len(scraped_map)} live records merged with static details.")
        return jsonify(master_data_copy)

    except Exception as e:
        print(f"Error connecting to database or processing data: {e}")
        print("Serving fallback data due to error.")
        return jsonify(FALLBACK_FLEET_DATA)


if __name__ == '__main__':
    print("Starting Flask server...")
    print("Your app will be available at http://127.0.0.1:5000/")
    app.run(debug=True, port=5000)