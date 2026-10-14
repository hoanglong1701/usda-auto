"""Doi ten nuoc (tieng Anh viet hoa trong bao cao USDA) sang tieng Viet dung tren web."""

# Thu tu quan trong: cum dai dat truoc cum ngan
_MAP = [
    ("UNKNOWN", "Chưa xác định nước đến"),
    ("KOREA, REPUBLIC", "Hàn Quốc"), ("BURMA", "Myanmar"), ("LAOS", "Lào"),
    ("POLAND", "Ba Lan"), ("SWEDEN", "Thụy Điển"), ("NORWAY", "Na Uy"), ("DENMARK", "Đan Mạch"),
    ("AUSTRIA", "Áo"), ("GREECE", "Hy Lạp"), ("SWITZERLAND", "Thụy Sĩ"), ("CYPRUS", "Síp"),
    ("MALTA", "Malta"), ("ALBANIA", "Albania"), ("KUWAIT", "Kuwait"), ("QATAR", "Qatar"),
    ("LEBANON", "Li-băng"), ("MOZAMBIQUE", "Mozambique"), ("SOMALIA", "Somalia"),
    ("LIBERIA", "Liberia"), ("GAMBIA", "Gambia"), ("GUYANA", "Guyana"), ("SURINAM", "Suriname"),
    ("TRINIDAD", "Trinidad và Tobago"), ("BAHAMAS", "Bahamas"), ("BARBADOS", "Barbados"),
    ("EUROPEAN UNION", "Liên minh châu Âu"),
    ("KOREA, SOUTH", "Hàn Quốc"), ("KOREA REP", "Hàn Quốc"), ("SOUTH KOREA", "Hàn Quốc"),
    ("CHINA", "Trung Quốc"), ("TAIWAN", "Đài Loan"), ("HONG KONG", "Hồng Kông"),
    ("JAPAN", "Nhật Bản"), ("MEXICO", "Mexico"), ("CANADA", "Canada"),
    ("COLOMBIA", "Colombia"), ("PERU", "Peru"), ("GUATEMALA", "Guatemala"),
    ("HONDURAS", "Honduras"), ("EL SALVADOR", "El Salvador"), ("NICARAGUA", "Nicaragua"),
    ("COSTA RICA", "Costa Rica"), ("PANAMA", "Panama"), ("BELIZE", "Belize"),
    ("JAMAICA", "Jamaica"), ("CUBA", "Cuba"), ("HAITI", "Haiti"),
    ("DOMINICAN", "Dominica"), ("VENEZUELA", "Venezuela"), ("ECUADOR", "Ecuador"),
    ("CHILE", "Chile"), ("BRAZIL", "Brazil"), ("ARGENTINA", "Argentina"),
    ("EGYPT", "Ai Cập"), ("MOROCCO", "Maroc"), ("ALGERIA", "Algeria"),
    ("TUNISIA", "Tunisia"), ("LIBYA", "Libya"), ("NIGERIA", "Nigeria"),
    ("GHANA", "Ghana"), ("SENEGAL", "Senegal"), ("KENYA", "Kenya"),
    ("SOUTH AFRICA", "Nam Phi"), ("ETHIOPIA", "Ethiopia"),
    ("NETHERLANDS", "Hà Lan"), ("GERMANY", "Đức"), ("SPAIN", "Tây Ban Nha"),
    ("ITALY", "Ý"), ("FRANCE", "Pháp"), ("BELGIUM", "Bỉ"), ("PORTUGAL", "Bồ Đào Nha"),
    ("UNITED KINGDOM", "Anh"), ("IRELAND", "Ireland"), ("TURKEY", "Thổ Nhĩ Kỳ"),
    ("ISRAEL", "Israel"), ("SAUDI", "Ả Rập Xê Út"), ("IRAQ", "Iraq"), ("IRAN", "Iran"),
    ("YEMEN", "Yemen"), ("JORDAN", "Jordan"), ("UNITED ARAB", "UAE"),
    ("INDONESIA", "Indonesia"), ("PHILIPPINES", "Philippines"), ("VIETNAM", "Việt Nam"),
    ("VIET NAM", "Việt Nam"), ("THAILAND", "Thái Lan"), ("MALAYSIA", "Malaysia"),
    ("SINGAPORE", "Singapore"), ("BANGLADESH", "Bangladesh"), ("PAKISTAN", "Pakistan"),
    ("INDIA", "Ấn Độ"), ("SRI LANKA", "Sri Lanka"), ("AUSTRALIA", "Úc"),
    ("NEW ZEALAND", "New Zealand"), ("RUSSIA", "Nga"), ("UKRAINE", "Ukraine"),
    ("BANGLADESH", "Bangladesh"), ("NEPAL", "Nepal"), ("MYANMAR", "Myanmar"),
    ("CAMBODIA", "Campuchia"),
]

unmapped = set()


def vn(desc):
    """desc: ten tieng Anh (bat ky kieu chu). Tra ve ten tieng Viet."""
    d = (desc or "").strip().upper()
    for k, v in _MAP:
        if k in d:
            return v
    unmapped.add(desc)
    return (desc or "").strip().title()
