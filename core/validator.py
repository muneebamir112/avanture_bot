import os
from pathlib import Path
from typing import Dict, List, Tuple
import pandas as pd
from config import REQUIRED_COLUMNS, OPTIONAL_COLUMNS, DATA_DIR, IMAGES_DIR, BASE_DIR, AVANTURE_CATEGORIES, AVANTURE_COUNTRIES

class ListingValidator:
    """Validates and prepares listing records for Avanture Classifieds."""

    @staticmethod
    def resolve_attachment_path(raw_val: any) -> Path | None:
        """Resolves an image/attachment path from absolute, relative, or data/images folder."""
        if not raw_val or pd.isna(raw_val):
            return None
        val_str = str(raw_val).strip()
        if not val_str:
            return None

        candidates = [
            Path(val_str),
            BASE_DIR / val_str,
            DATA_DIR / val_str,
            IMAGES_DIR / val_str,
            DATA_DIR / "images" / val_str
        ]
        for c in candidates:
            if c.exists() and c.is_file():
                return c.resolve()
        return None

    @staticmethod
    def get_attachment_raw(row: pd.Series) -> any:
        """Finds attachment path using multiple column name aliases."""
        for col in ["attachment_path", "photo", "image", "picture", "attachment", "slika", "priloga"]:
            if col in row and pd.notna(row.get(col)):
                val = str(row.get(col)).strip()
                if val:
                    return val
        return None

    @staticmethod
    def load_data(file_path: str) -> Tuple[bool, str, pd.DataFrame]:
        path = Path(file_path)
        if not path.exists():
            return False, f"File does not exist: {file_path}", pd.DataFrame()

        try:
            if path.suffix.lower() in ['.xlsx', '.xls']:
                df = pd.read_excel(file_path)
            elif path.suffix.lower() == '.csv':
                df = pd.read_csv(file_path)
            else:
                return False, "Unsupported file format. Please provide a .csv or .xlsx file.", pd.DataFrame()

            # Clean column names
            df.columns = [str(col).strip().lower().replace(" ", "_") for col in df.columns]

            missing_cols = [col for col in REQUIRED_COLUMNS if col not in df.columns]
            if missing_cols:
                return False, f"Missing required columns: {', '.join(missing_cols)}", df

            if "_status" not in df.columns:
                df["_status"] = "PENDING"
            if "_error_msg" not in df.columns:
                df["_error_msg"] = ""

            return True, f"Successfully loaded {len(df)} records.", df

        except Exception as e:
            return False, f"Error reading file: {str(e)}", pd.DataFrame()

    @staticmethod
    def validate_row(row: pd.Series) -> Tuple[bool, str]:
        # 1. Title validation
        title = str(row.get("title", "")).strip()
        if not title:
            return False, "Title is required"
        if len(title) > 50:
            return False, f"Title exceeds 50 characters ({len(title)} chars)"

        # 2. Category validation
        cat = str(row.get("category", "")).strip()
        if not cat:
            return False, "Category is required"

        # 3. Description validation (min 50, max 1000)
        desc = str(row.get("description", "")).strip()
        if not desc:
            return False, "Description is required"
        if len(desc) < 50:
            return False, f"Description must be at least 50 characters (currently {len(desc)})"
        if len(desc) > 1000:
            return False, f"Description exceeds 1000 characters ({len(desc)} chars)"

        # 4. Attachment path if provided
        att_raw = ListingValidator.get_attachment_raw(row)
        if att_raw:
            resolved = ListingValidator.resolve_attachment_path(att_raw)
            if not resolved:
                return False, f"Attachment image file not found on disk: '{att_raw}'. Checked absolute path, project folder, and data/images/."

        return True, "Valid"

    @staticmethod
    def generate_sample_template(target_path: str = None) -> str:
        if not target_path:
            target_path = DATA_DIR / "sample_listings_template.xlsx"
        else:
            target_path = Path(target_path)

        sample_rows = [
            {
                "title": "A relaxed evening for two in Ljubljana",
                "category": "He seeks her",
                "description": "Looking for a pleasant, mature company for dinner, wine, and casual conversation. Polite and respectful gentleman.",
                "country": "Slovenia",
                "state": "Osrednjeslovenska",
                "city": "Ljubljana",
                "registration_number": "",
                "attachment_path": ""
            },
            {
                "title": "Seeking friendly conversation and fun",
                "category": "Virtual",
                "description": "Available for virtual chats, video calls, and sharing interesting hobbies online. Genuine inquiries only please.",
                "country": "Croatia",
                "state": "Grad Zagreb",
                "city": "Zagreb",
                "registration_number": "",
                "attachment_path": ""
            }
        ]

        df = pd.DataFrame(sample_rows)
        df.to_excel(target_path, index=False)
        return str(target_path)
