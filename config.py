import os
import sys
from pathlib import Path

# Base Paths
BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
IMAGES_DIR = DATA_DIR / "images"
LOGS_DIR = BASE_DIR / "logs"
SCREENSHOTS_DIR = BASE_DIR / "screenshots"
SESSION_FILE = BASE_DIR / "session.json"
REMEMBER_ME_FILE = BASE_DIR / ".remember_me.json"
AVANTURE_CREDS_FILE = BASE_DIR / ".avanture_creds.json"

# Ensure directories exist
for path in [DATA_DIR, IMAGES_DIR, LOGS_DIR, SCREENSHOTS_DIR]:
    path.mkdir(exist_ok=True)

# Application Defaults
HOME_URL = "https://www.avanture.net/"
DEFAULT_TARGET_URL = "https://www.avanture.net/"
CLASSIFIEDS_URL = "https://www.avanture.net/classifieds"
LOGIN_URL = "https://www.avanture.net/users/login"
DEFAULT_DELAY_MIN = 2.0  # seconds
DEFAULT_DELAY_MAX = 4.0  # seconds
DEFAULT_TIMEOUT_MS = 30000  # 30 seconds
DEFAULT_PROXY = ""  # e.g. "http://ip:port" or "socks5://ip:port"

# Chrome Profile Defaults (Cross-Platform: Windows, macOS, Linux)
if sys.platform == "darwin":  # macOS
    CHROME_PATH = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
    CHROME_USER_DATA_DIR = os.path.expanduser("~/Library/Application Support/Google/Chrome")
elif sys.platform == "win32":  # Windows
    CHROME_PATH = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
    CHROME_USER_DATA_DIR = os.path.expandvars(r"%LOCALAPPDATA%\Google\Chrome\User Data")
else:  # Linux
    CHROME_PATH = "/usr/bin/google-chrome"
    CHROME_USER_DATA_DIR = os.path.expanduser("~/.config/google-chrome")

CHROME_PROFILE_DEFAULT = "Default"
CDP_URL = "http://127.0.0.1:9222"

# Central Auth Server & Remote Revocation URL
# If auth_server_url.txt exists, its contents take precedence
AUTH_SERVER_CONFIG_FILE = BASE_DIR / "auth_server_url.txt"
if AUTH_SERVER_CONFIG_FILE.exists():
    try:
        AUTH_SERVER_URL = AUTH_SERVER_CONFIG_FILE.read_text(encoding="utf-8").strip()
    except Exception:
        AUTH_SERVER_URL = "http://localhost:8000"
else:
    AUTH_SERVER_URL = os.environ.get("AUTH_SERVER_URL", "http://localhost:8000")

# Listing template columns
REQUIRED_COLUMNS = [
    "title",
    "category",
    "description"
]

OPTIONAL_COLUMNS = [
    "country",
    "state",
    "city",
    "registration_number",
    "attachment_path"
]

# Avanture Category Mapping (English & Slovenian Names -> Value)
AVANTURE_CATEGORIES = {
    # Female categories (Venus / Female account)
    "she seeks him": "1",
    "ona isce njega": "1",
    "ona išče njega": "1",
    "she seeks him (ona išče njega)": "1",
    "she seeks her": "2",
    "ona isce njo": "2",
    "ona išče njo": "2",
    "she seeks her (ona išče njo)": "2",
    "she seeks couple": "3",
    "ona isce par": "3",
    "ona išče par": "3",
    "she seeks couple (ona išče par)": "3",
    "female escort": "4",
    "she offers companionship": "4",
    "ona nudi spremstvo": "4",
    "female escort (ona nudi spremstvo)": "4",
    # Male categories
    "he seeks her": "5",
    "he seeks her (on išče njo)": "5",
    "he seeks him": "6",
    "he seeks him (on išče njega)": "6",
    "he seeks couple": "7",
    "he seeks couple (on išče par)": "7",
    "male escort": "8",
    "male escort (moški spremljevalec)": "8",
    # Common categories
    "seeking trans": "14",
    "iscem trans": "14",
    "iščem trans": "14",
    "seeking trans (iščem trans)": "14",
    "dominant looking": "16",
    "dominanten/a isce": "16",
    "dominanten/a išče": "16",
    "dominant looking (dominanten/a išče)": "16",
    "submissive looking": "17",
    "submisiven/a isce": "17",
    "submisiven/a išče": "17",
    "submissive looking (submisiven/a išče)": "17",
    "switch looking": "18",
    "switch isce": "18",
    "switch išče": "18",
    "switch looking (switch išče)": "18",
    "kink & fetish": "19",
    "kink & fetiš": "19",
    "kink": "19",
    "fetis": "19",
    "virtual": "20",
    "virtualno": "20",
    "only fans": "21",
    "onlyfans": "21",
    "erotic massage": "22",
    "eroticne masaze": "22",
    "erotične masaže": "22",
    "serious relationship": "23",
    "resna zveza": "23",
    "resne zveze": "23",
    "short stay": "24",
    "kratka zveza": "24",
    "avantura": "24",
    "dnevni pocitek": "24",
    "dnevni počitek": "24",
    "sex toys": "25",
    "seks igracke": "25",
    "seks igračke": "25",
    "eroticne igracke": "25",
    "erotične igračke": "25",
    "events": "26",
    "dogodki": "26",
    "other": "27",
    "ostalo": "27",
    # Slovenian Male
    "on isce njo": "5",
    "on išče njo": "5",
    "on isce njega": "6",
    "on išče njega": "6",
    "on isce par": "7",
    "on išče par": "7",
    "moski spremljevalec": "8",
    "moški spremljevalec": "8"
}

# Avanture Country Mapping (English & Slovenian Names -> Value)
AVANTURE_COUNTRIES = {
    "austria": "197",
    "avstrija": "197",
    "bosnia and herzegovina": "187",
    "bosna in hercegovina": "187",
    "croatia": "186",
    "hrvaska": "186",
    "hrvaška": "186",
    "hungary": "195",
    "madzarska": "195",
    "madžarska": "195",
    "italy": "169",
    "italija": "169",
    "serbia and montenegro": "184",
    "srbija in crna gora": "184",
    "srbija in črna gora": "184",
    "slovenia": "193",
    "slovenija": "193"
}

# Scraped Slovenia Locations (State -> Cities Hierarchy)
AVANTURE_SLOVENIA_LOCATIONS = {
    "Osrednjeslovenska": [
        "Ljubljana", "Borovnica", "Brezovica pri Ljubljani", "Dob", "Dobrova", "Domžale",
        "Dragomer", "Grosuplje", "Horjul", "Ig", "Kamnik", "Komenda", "Litija", "Logatec",
        "Medvode", "Mekinje", "Mengeš", "Moravče", "Podgorje", "Radomlje", "Rovte",
        "Škofljica", "Šmarca", "Trzin", "Verd", "Vir", "Vnanje Gorice", "Vodice", "Vrhnika"
    ],
    "Podravska": [
        "Maribor", "Bresternica", "Bukovci", "Dogoše", "Dornava", "Fram", "Kamnica",
        "Kidričevo", "Lenart", "Limbuš", "Lovrenc na Pohorju", "Miklavž na Dravskem Polju",
        "Ormož", "Pekre", "Pesnica pri Mariboru", "Podvinci", "Poljčane", "Pragersko",
        "Ptuj", "Rače", "Radizel", "Razvanje", "Rogoza", "Ruše", "Šentilj", "Skoke",
        "Slovenska Bistrica", "Spodnje Hoče", "Spuhlja", "Stojnci"
    ],
    "Obalno-kraška": [
        "Koper", "Ankaran", "Bertoki", "Dekani", "Divača", "Izola", "Jagodje", "Lucija",
        "Piran", "Pobegi", "Portorož", "Sežana"
    ],
    "Savinjska": [
        "Celje", "Gotovlje", "Kasaze", "Laško", "Ljubečna", "Lokovica", "Mozirje", "Nazarje",
        "Oplotnica", "Petrovče", "Polzela", "Prebold", "Radeče", "Ravne", "Rogaška Slatina",
        "Šempeter", "Šentjur", "Škale", "Slovenske Konjice", "Šoštanj", "Štore", "Topolšica",
        "Velenje", "Vitanje", "Vojnik", "Zabukovica", "Žalec", "Zreče"
    ],
    "Gorenjska": [
        "Kranj", "Bistrica ob Tržiču", "Bled", "Britof", "Golnik", "Hrušica", "Jesenice",
        "Kokrica", "Koroška Bela", "Kranjska Gora", "Križe", "Kropa", "Lesce", "Mojstrana",
        "Preddvor", "Predoslje", "Radovljica", "Šenčur", "Škofja Loka", "Slovenski Javornik",
        "Tržič", "Visoko", "Železniki", "Žiri"
    ],
    "Goriška": [
        "Ajdovščina", "Bilje", "Branik", "Cerkno", "Deskle", "Idrija", "Kanal", "Kobarid",
        "Kromberk", "Lokavec", "Miren", "Nova Gorica", "Prvačina", "Renče", "Šempas",
        "Šempeter", "Solkan", "Spodnja Idrija", "Tolmin", "Vipava", "Vrtojba"
    ],
    "Jugovzhodna": [
        "Novo Mesto", "Črnomelj", "Kočevje", "Kotlje", "Metlika", "Mirna", "Ribnica",
        "Straža", "Trebnje", "Žužemberk"
    ],
    "Koroška": [
        "Slovenj Gradec", "Črna na Koroškem", "Dravograd", "Legen", "Mežica", "Mislinja",
        "Muta", "Pameče", "Podgorje", "Prevalje", "Radlje ob Dravi", "Ravne", "Vuhred", "Vuzenica"
    ],
    "Notranjsko-kraška": [
        "Postojna", "Cerknica", "Ilirska Bistrica", "Pivka", "Rakek"
    ],
    "Pomurska": [
        "Murska Sobota", "Bakovci", "Beltinci", "Černelavci", "Črenšovci", "Dobrovnik",
        "Dokležovje", "Gančani", "Gornja Radgona", "Ižakovci", "Krog", "Lendava", "Lipovci",
        "Ljutomer", "Melinci", "Odranci", "Petišovci", "Radenci", "Rakičan", "Turnišče", "Verzej"
    ],
    "Spodnjeposavska": [
        "Krško", "Brestanica", "Brežice", "Senovo", "Sevnica"
    ],
    "Zasavska": [
        "Trbovlje", "Hrastnik", "Izlake", "Zagorje ob Savi"
    ]
}
