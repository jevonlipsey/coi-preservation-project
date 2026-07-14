import os
import re
import pandas as pd

### config
DATA_DIR = os.path.join(os.path.dirname(__file__), "data", "public-comments")
OUT_FILE = os.path.join(
    os.path.dirname(__file__), "data/public-comments", "agg_co_comments.csv"
)

TARGET_COLS = [
    "source_file",
    "commenter_id",
    "zip_code",
    "commission_level",
    "comment_text",
]


def clean_text(val):
    """strip newlines/carriage returns, fix encoding, handle nan gracefully"""
    if pd.isna(val):
        return ""
    return fix_encoding(str(val))


# cp1252 mojibake -> correct unicode char map (ordered longest-match first)
# these appear when utf-8 bytes were decoded as windows-1252 at some earlier step
_MOJIBAKE_MAP = [
    ("â€œ", "\u201c"),  # left double quote "
    ("â€\x9d", "\u201d"),  # right double quote " (after _x009d_ substitution)
    ("â€™", "\u2019"),  # apostrophe / right single quote '
    ('â€"', "\u2013"),  # en dash -
    ('â€"', "\u2014"),  # em dash --
    ("â€¢", "\u2022"),  # bullet point *
    ("â€¦", "\u2026"),  # ellipsis ...
    ("â€˜", "\u2018"),  # left single quote '
    ("â€ž", "\u201e"),  # double low-9 quotation mark
    ("â€¹", "\u2039"),  # single left-pointing angle quotation
    ("â€º", "\u203a"),  # single right-pointing angle quotation
    ("â€°", "\u2030"),  # per mille sign
    ("â„¢", "\u2122"),  # trademark sign
    ("â€", "\u201d"),  # right double quote fallback (2-char, after 3-char above)
    ("Ã¡", "\u00e1"),  # a-acute: á
    ("Ã©", "\u00e9"),  # e-acute: é
    ("Ã­", "\u00ed"),  # i-acute: í
    ("Ã³", "\u00f3"),  # o-acute: ó
    ("Ãº", "\u00fa"),  # u-acute: ú
    ("Ã±", "\u00f1"),  # n-tilde: ñ
    ("Ã ", "\u00e0"),  # a-grave: à
    ("Ã¨", "\u00e8"),  # e-grave: è
    ("Ã¬", "\u00ec"),  # i-grave: ì
    ("Ã²", "\u00f2"),  # o-grave: ò
    ("Ã¹", "\u00f9"),  # u-grave: ù
    ("Ã¢", "\u00e2"),  # a-circumflex: â
    ("Â·", "\u00b7"),  # middle dot
    ("Â°", "\u00b0"),  # degree sign
    ("Â½", "\u00bd"),  # vulgar fraction one half
    ("Â¼", "\u00bc"),  # vulgar fraction one quarter
    ("Â¾", "\u00be"),  # vulgar fraction three quarters
    ("Â©", "\u00a9"),  # copyright
    ("Â®", "\u00ae"),  # registered trademark
    ("Âµ", "\u00b5"),  # micro sign
    ("Ã‰", "\u00c9"),  # E-acute: É
    ("Ã‡", "\u00c7"),  # C-cedilla: Ç
]


def fix_encoding(text):
    """
    fix cp1252 mojibake and excel _xNNNN_ hex escapes in a string

    inputs:
    text: raw comment string that may contain garbled characters
    outputs:
    text: cleaned string with proper unicode punctuation and accents
    """
    if not isinstance(text, str):
        return text
    # 1. replace _xNNNN_ excel escapes with actual unicode chars
    #    do this before mojibake fix so â€_x009d_ -> â€\x9d -> " correctly
    text = re.sub(r"_x([0-9A-Fa-f]{4})_", lambda m: chr(int(m.group(1), 16)), text)
    # 2. apply mojibake map (longest sequences first)
    for garbled, correct in _MOJIBAKE_MAP:
        text = text.replace(garbled, correct)
    # 3. strip remaining C1 control char artifacts left by partial sequences
    text = text.replace("\x9d", "").replace("\x80", "").replace("\x9c", "")
    # 4. normalize whitespace artifacts
    text = text.replace("\xa0", " ")  # no-break space -> space
    text = text.replace("\xad", "")  # soft hyphen -> remove
    text = re.sub(r"[\n\r\x0b\x0c]", " ", text)
    text = re.sub(r"  +", " ", text).strip()
    return text


def norm_commission(val):
    """
    normalize commission strings to congressional / legislative / both/unknown

    inputs:
    val: raw commission string or nan
    outputs:
    str: one of the three canonical values
    """
    if pd.isna(val):
        return "both/unknown"
    v = str(val).strip().lower()
    if v in ("congressional", "congress"):
        return "congressional"
    if v in ("legislative", "state legislative"):
        return "legislative"
    if v in ("both", "both commissions"):
        return "both/unknown"
    return "both/unknown"


def norm_zip(val):
    """
    normalize zip to clean 5-digit string or empty string

    rules applied in order:
    - nan -> ''
    - strip whitespace, strip trailing .0 (float artifact)
    - strip hyphen suffix (80302-4304 -> 80302)
    - strip leading zeros that inflated digit count
    - >6 digits -> likely phone number entered by mistake -> ''
    - exactly 6 digits -> assume last digit is a typo, take first 5
    - 9-digit zip+4 without hyphen -> take first 5
    - 0 or '0' -> clearly invalid -> ''
    - non-5-digit result -> ''
    """
    if pd.isna(val):
        return ""
    s = str(val).strip()
    # drop float artifact
    if s.endswith(".0"):
        s = s[:-2]
    # strip hyphen suffix (zip+4 with hyphen)
    s = s.split("-")[0].strip()
    # must be all digits now to be a valid zip
    if not s.isdigit():
        return ""
    # clearly invalid sentinel
    if s == "0" or s == "":
        return ""
    # phone numbers (10 digits) or other long junk
    if len(s) > 6:
        return ""
    # 9-digit zip+4 without hyphen - take first 5
    if len(s) == 9:
        return s[:5]
    # 6 digits - most likely a typo on the last digit, take first 5
    if len(s) == 6:
        return s[:5]
    # less than 4 digits - too short to be valid
    if len(s) < 4:
        return ""
    # 4 digits might be a truncated zip (e.g. leading 0 dropped) - leave blank
    if len(s) == 4:
        return ""
    # exactly 5 - good
    return s


def make_frame(
    df, source, commenter_id_col, zip_col, commission_col, comment_col, summary_col=None
):
    """
    build a target-schema dataframe from a raw df

    inputs:
    df: raw dataframe
    source: filename string
    commenter_id_col: column name for commenter id (or None)
    zip_col: column name for zip (or None)
    commission_col: column name for commission (or None)
    summary_col: optional column to prepend to comment_col
    outputs:
    out: dataframe with TARGET_COLS
    """
    out = pd.DataFrame(index=df.index)
    out["source_file"] = source  # broadcasts scalar to full length

    # commenter id
    out["commenter_id"] = (
        df[commenter_id_col].apply(clean_text) if commenter_id_col else ""
    )

    # zip
    out["zip_code"] = df[zip_col].apply(norm_zip) if zip_col else ""

    # commission
    out["commission_level"] = (
        df[commission_col].apply(norm_commission) if commission_col else "both/unknown"
    )

    # comment text - concat summary + full comment if both present
    if (
        summary_col
        and summary_col in df.columns
        and comment_col
        and comment_col in df.columns
    ):
        out["comment_text"] = df.apply(
            lambda r: (
                clean_text(r[summary_col]) + " " + clean_text(r[comment_col])
            ).strip(),
            axis=1,
        )
    elif comment_col and comment_col in df.columns:
        out["comment_text"] = df[comment_col].apply(clean_text)
    else:
        out["comment_text"] = ""

    return out[TARGET_COLS]


### per-file handlers
# each function returns a dataframe with TARGET_COLS


def process_sheet1_9_25_9_28(path):
    """
    'Public Comment  9_25 9_28 - Sheet1.csv'
    headerless: cols are id, email, name, timestamp, commission, zip, comment, key_phrase
    infer commission_level from col 4
    """
    df = pd.read_csv(path, header=None)
    df.columns = [
        "id",
        "email",
        "name",
        "updated_at",
        "commission",
        "zip",
        "comment",
        "key_phrase",
    ]
    # commenter_id = email if present, else name
    df["commenter_id_raw"] = df.apply(
        lambda r: (
            r["email"]
            if pd.notna(r["email"]) and str(r["email"]).strip()
            else r["name"]
        ),
        axis=1,
    )
    return make_frame(
        df,
        os.path.basename(path),
        commenter_id_col="commenter_id_raw",
        zip_col="zip",
        commission_col="commission",
        comment_col="comment",
    )


def process_sheet2_9_25_9_28(path):
    """
    'Public Comment  9_25 9_28 - Sheet2.csv'
    same headerless schema as Sheet1 - commission is legislative based on filename context
    """
    df = pd.read_csv(path, header=None)
    df.columns = [
        "id",
        "email",
        "name",
        "updated_at",
        "commission",
        "zip",
        "comment",
        "key_phrase",
    ]
    df["commenter_id_raw"] = df.apply(
        lambda r: (
            r["email"]
            if pd.notna(r["email"]) and str(r["email"]).strip()
            else r["name"]
        ),
        axis=1,
    )
    return make_frame(
        df,
        os.path.basename(path),
        commenter_id_col="commenter_id_raw",
        zip_col="zip",
        commission_col="commission",
        comment_col="comment",
    )


def process_section3(path):
    """
    'Public Comment Report Section 3 - ... - *.csv'
    4 files share the same schema:
    Comment ID, Comment Type, Commission, Zip, Source, COI, ..., Summary, ..., Full Comment, Links
    concat Summary + Full Comment into comment_text
    commenter_id = 'Comment ID' (contains name/date string like '060121 Baca County...')
    """
    df = pd.read_csv(path, low_memory=False)
    return make_frame(
        df,
        os.path.basename(path),
        commenter_id_col="Comment ID",
        zip_col="Zip",
        commission_col="Commission",
        comment_col="Full Comment",
        summary_col="Summary",
    )


def process_9_20_9_24_legislative(path):
    """
    'public-comments-9_20 - 9_24 - Legislative.csv'
    headerless: id, email, name, timestamp, commission, zip, comment
    note: no key_phrase col confirmed by checking - same schema as sheet1 but without trailing col
    handle variable col count gracefully
    """
    df = pd.read_csv(path, header=None)
    # assign only cols we know exist
    base_cols = ["id", "email", "name", "updated_at", "commission", "zip", "comment"]
    if len(df.columns) >= 8:
        base_cols.append("key_phrase")
    df.columns = base_cols[: len(df.columns)]
    df["commenter_id_raw"] = df.apply(
        lambda r: (
            r["email"]
            if pd.notna(r["email"]) and str(r["email"]).strip()
            else r["name"]
        ),
        axis=1,
    )
    # commission col exists but file is legislative - keep data-driven value
    return make_frame(
        df,
        os.path.basename(path),
        commenter_id_col="commenter_id_raw",
        zip_col="zip",
        commission_col="commission",
        comment_col="comment",
    )


def process_9_20_9_24_congressional(path):
    """
    'public-comments-9_20 - 9_24 - public-comments-2021-09-21.csv'
    has header: id, email, name, updated_at, commission, zip, comment, Key Work Phrase
    """
    df = pd.read_csv(path)
    df.columns = [c.strip() for c in df.columns]
    df["commenter_id_raw"] = df.apply(
        lambda r: (
            r["email"]
            if pd.notna(r["email"]) and str(r["email"]).strip()
            else r["name"]
        ),
        axis=1,
    )
    return make_frame(
        df,
        os.path.basename(path),
        commenter_id_col="commenter_id_raw",
        zip_col="zip",
        commission_col="commission",
        comment_col="comment",
    )


def process_9_20_9_21_legislative(path):
    """
    'public-comments-9_20 & 9_21 - Legislative.csv'
    headerless, same schema as the 9_24 legislative file
    """
    df = pd.read_csv(path, header=None)
    base_cols = ["id", "email", "name", "updated_at", "commission", "zip", "comment"]
    if len(df.columns) >= 8:
        base_cols.append("key_phrase")
    df.columns = base_cols[: len(df.columns)]
    df["commenter_id_raw"] = df.apply(
        lambda r: (
            r["email"]
            if pd.notna(r["email"]) and str(r["email"]).strip()
            else r["name"]
        ),
        axis=1,
    )
    return make_frame(
        df,
        os.path.basename(path),
        commenter_id_col="commenter_id_raw",
        zip_col="zip",
        commission_col="commission",
        comment_col="comment",
    )


def process_9_20_9_21_congressional(path):
    """
    'public-comments-9_20 & 9_21 - public-comments-2021-09-21.csv'
    has header: id, email, name, updated_at, commission, zip, comment, Key Work Phrase
    """
    df = pd.read_csv(path)
    df.columns = [c.strip() for c in df.columns]
    df["commenter_id_raw"] = df.apply(
        lambda r: (
            r["email"]
            if pd.notna(r["email"]) and str(r["email"]).strip()
            else r["name"]
        ),
        axis=1,
    )
    return make_frame(
        df,
        os.path.basename(path),
        commenter_id_col="commenter_id_raw",
        zip_col="zip",
        commission_col="commission",
        comment_col="comment",
    )


def process_aug28_sept10(path):
    """
    'Public-comments-Aug28-Sept9 - public-comments-Aug28-Sept10.csv'
    has header: id, email, Name, updated_at, commission, zip, Comment Summary, Comment Type, Comment Area, Maps, Comment
    concat 'Comment Summary' + 'Comment' for comment_text
    """
    df = pd.read_csv(path)
    df.columns = [c.strip() for c in df.columns]
    df["commenter_id_raw"] = df.apply(
        lambda r: (
            r["email"]
            if pd.notna(r["email"]) and str(r["email"]).strip()
            else r["Name"]
        ),
        axis=1,
    )
    return make_frame(
        df,
        os.path.basename(path),
        commenter_id_col="commenter_id_raw",
        zip_col="zip",
        commission_col="commission",
        comment_col="Comment",
        summary_col="Comment Summary",
    )


def process_sept11_13(path):
    """
    'Public-comments-Sept10-15 - Public-comments-Sept11-13.csv'
    has header: name, commission, comment, Summary, Key Word Phrase, Comment Type
    no email, no zip col
    concat Summary + comment for comment_text
    """
    df = pd.read_csv(path)
    df.columns = [c.strip() for c in df.columns]
    return make_frame(
        df,
        os.path.basename(path),
        commenter_id_col="name",
        zip_col=None,
        commission_col="commission",
        comment_col="comment",
        summary_col="Summary",
    )


### main

FILES = {
    "Public Comment  9_25 9_28 - Sheet1.csv": process_sheet1_9_25_9_28,
    "Public Comment  9_25 9_28 - Sheet2.csv": process_sheet2_9_25_9_28,
    "Public Comment Report Section 3 - Western-Eastern and Southern Comments Aug30 2021 (see tabs) - Eastern Plains, Western Slope.csv": process_section3,
    "Public Comment Report Section 3 - Western-Eastern and Southern Comments Aug30 2021 (see tabs) - Pueblo (southern).csv": process_section3,
    "Public Comment Report Section 3 - Western-Eastern and Southern Comments Aug30 2021 (see tabs) - Southern Colorado.csv": process_section3,
    "Public Comment Report Section 3 - Western-Eastern and Southern Comments Aug30 2021 (see tabs) - Want CD3 Split.csv": process_section3,
    "public-comments-9_20 - 9_24 - Legislative.csv": process_9_20_9_24_legislative,
    "public-comments-9_20 - 9_24 - public-comments-2021-09-21.csv": process_9_20_9_24_congressional,
    "public-comments-9_20 & 9_21 - Legislative.csv": process_9_20_9_21_legislative,
    "public-comments-9_20 & 9_21 - public-comments-2021-09-21.csv": process_9_20_9_21_congressional,
    "Public-comments-Aug28-Sept9 - public-comments-Aug28-Sept10.csv": process_aug28_sept10,
    "Public-comments-Sept10-15 - Public-comments-Sept11-13.csv": process_sept11_13,
}


def main():
    frames = []
    # append all csvs together
    for fname, handler in FILES.items():
        fpath = os.path.join(DATA_DIR, fname)
        if not os.path.exists(fpath):
            print(f"  warning: {fname} not found, skipping")
            continue
        print(f"processing {fname}...")
        df = handler(fpath)
        print(f"  -> {len(df)} rows")
        frames.append(df)

    main = pd.concat(frames, ignore_index=True)

    # cleanup pass
    main["comment_text"] = main["comment_text"].apply(clean_text)
    main["commenter_id"] = main["commenter_id"].apply(clean_text)
    # zip: keep as string, empty string where unknown
    main["zip_code"] = main["zip_code"].fillna("").astype(str).str.strip()

    # drop fully empty comment rows - no signal for nlp
    main = main[main["comment_text"].str.len() > 0].reset_index(drop=True)

    print(f"\nmaster shape: {main.shape}")
    print(main["commission_level"].value_counts())
    print(main["source_file"].value_counts())

    main.to_csv(OUT_FILE, index=False)
    print(f"\nsaved -> {OUT_FILE}")


if __name__ == "__main__":
    main()
