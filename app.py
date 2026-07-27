import os
import time
import urllib.parse
import streamlit as st
import google.genai as genai
from PIL import Image
from pypdf import PdfReader
from supabase import create_client, Client

st.set_page_config(page_title="AI Paper Marker Pro & MCQ Evaluator", page_icon="📝", layout="wide")

# 1. Setup Supabase & Gemini Credentials from Secrets
SUPABASE_URL = st.secrets.get("SUPABASE_URL", os.environ.get("SUPABASE_URL"))
SUPABASE_KEY = st.secrets.get("SUPABASE_KEY", os.environ.get("SUPABASE_KEY"))
GEMINI_API_KEY = st.secrets.get("GEMINI_API_KEY", os.environ.get("GEMINI_API_KEY"))

if not SUPABASE_URL or not SUPABASE_KEY or not GEMINI_API_KEY:
    st.error("Secrets (SUPABASE_URL, SUPABASE_KEY, GEMINI_API_KEY) සෙට් කර නොමැත.")
    st.stop()

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
client = genai.Client(api_key=GEMINI_API_KEY)

# Initialize Session States
if "user" not in st.session_state:
    st.session_state.user = None

if "evaluation_result" not in st.session_state:
    st.session_state.evaluation_result = None

def get_user_credits(user_id):
    try:
        res = supabase.table("profiles").select("credits").eq("id", user_id).single().execute()
        return res.data["credits"] if res.data else 0
    except Exception:
        return 0

def deduct_credit(user_id, current_credits):
    supabase.table("profiles").update({"credits": current_credits - 1}).eq("id", user_id).execute()

# --- HELPER FUNCTION TO EXTRACT TEXT FROM PDF ---
def extract_text_from_pdf(pdf_file):
    try:
        reader = PdfReader(pdf_file)
        text = ""
        for page in reader.pages:
            extracted = page.extract_text()
            if extracted:
                text += extracted + "\n"
        return text
    except Exception as e:
        st.error(f"PDF කියවීමේ දෝෂයක්: {str(e)}")
        return ""

# --- SAFE & STABLE GEMINI GENERATION FUNCTION ---
def generate_content_with_fallback(client, contents):
    """
    Uses only verified working model identifiers for google-genai SDK.
    Retries automatically if the server experiences temporary 503 overload.
    """
    valid_models = ['gemini-2.5-flash', 'gemini-2.0-flash']
    last_exception = None

    for model_name in valid_models:
        # Try up to 2 times per model with delay for temporary 503 errors
        for attempt in range(2):
            try:
                response = client.models.generate_content(
                    model=model_name,
                    contents=contents
                )
                return response
            except Exception as e:
                last_exception = e
                time.sleep(2)  # Wait 2 seconds before retrying
                continue
    
    raise last_exception

# --- LOGIN / SIGNUP SIDEBAR ---
st.sidebar.title("👤 User Account")

if not st.session_state.user:
    auth_mode = st.sidebar.radio("Action", ["Login", "Sign Up"])
    email = st.sidebar.text_input("Email")
    password = st.sidebar.text_input("Password", type="password")

    if auth_mode == "Sign Up":
        if st.sidebar.button("Create Account"):
            try:
                res = supabase.auth.sign_up({"email": email, "password": password})
                st.sidebar.success("Account එක සාර්ථකව සෑදුවා! දැන් Login වන්න.")
            except Exception as e:
                st.sidebar.error(f"Error: {e}")

    elif auth_mode == "Login":
        if st.sidebar.button("Login"):
            try:
                res = supabase.auth.sign_in_with_password({"email": email, "password": password})
                st.session_state.user = res.user
                st.session_state.evaluation_result = None
                st.rerun()
            except Exception as e:
                st.sidebar.error("Login අසාර්ථකයි. Email/Password පරීක්ෂා කරන්න.")

else:
    user_id = st.session_state.user.id
    user_email = st.session_state.user.email
    credits = get_user_credits(user_id)

    st.sidebar.write(f"Logged in as: **{user_email}**")
    st.sidebar.metric(label="Remaining Marking Credits", value=credits)

    st.sidebar.markdown("---")
    st.sidebar.subheader("💳 Buy More Credits")
    st.sidebar.write("රු. 1,000/= (Credits 100)")
    
    PAYHERE_MERCHANT_ID = st.secrets.get("PAYHERE_MERCHANT_ID", "123456")
    payhere_url = f"https://www.payhere.lk/pay/checkout?merchant_id={PAYHERE_MERCHANT_ID}&items=Paper+Marking+100+Credits&amount=1000&currency=LKR&custom_1={user_id}"
    
    st.sidebar.markdown(f"[👉 Pay via PayHere (Card / eZ Cash)]({payhere_url})", unsafe_allow_html=True)

    # --- WHATSAPP RECEIPT BUTTON ---
    whatsapp_number = "94712382306"
    whatsapp_msg = f"Hello! I made a payment for AI Paper Marker Credits.\nUser Email: {user_email}\nUser ID: {user_id}\nPlease find my attached payment receipt/slip."
    encoded_msg = urllib.parse.quote(whatsapp_msg)
    whatsapp_url = f"https://wa.me/{whatsapp_number}?text={encoded_msg}"

    st.sidebar.markdown(
        f'<a href="{whatsapp_url}" target="_blank" style="text-decoration: none;"><div style="background-color: #25D366; color: white; padding: 10px; border-radius: 8px; text-align: center; font-weight: bold; margin-top: 10px; margin-bottom: 10px;">💬 WhatsApp හරහා Slip එක එවන්න</div></a>',
        unsafe_allow_html=True
    )

    if st.sidebar.button("Logout"):
        st.session_state.user = None
        st.session_state.evaluation_result = None
        st.rerun()

# --- MAIN APPLICATION ---
st.title("📝 School AI Paper Marking & MCQ Evaluator")

if not st.session_state.user:
    st.info("👋 Platform එක භාවිත කිරීමට කරුණාකර Sidebar එකෙන් Login වන්න හෝ නොමිලේ Account එකක් සාදාගන්න (Free 5 Credits ලැබෙනු ඇත).")
else:
    user_id = st.session_state.user.id
    credits = get_user_credits(user_id)

    paper_type = st.radio("📄 Select Paper Mode:", ["MCQ Answer Sheet (OMR / Multi-choice)", "Essay / Structured Essay Paper"], horizontal=True)

    col1, col2 = st.columns(2)

    with col1:
        st.subheader("1. Marking Scheme / Key Answers")
        scheme_file = st.file_uploader("Upload Marking Scheme (Image or PDF)", type=["jpg", "jpeg", "png", "pdf"], key="scheme")
        
        pdf_extracted_text = ""
        if scheme_file:
            if scheme_file.type == "application/pdf":
                st.success("📄 PDF Marking Scheme Loaded Successfully!")
                pdf_extracted_text = extract_text_from_pdf(scheme_file)
            else:
                st.image(scheme_file, use_container_width=True)

        scheme_text = st.text_area(
            "Or Type Correct Answers (e.g., 1-2, 2-4, 3-1 or 1-A, 2-C)", 
            height=120, 
            placeholder="MCQ Key Example:\n1 - (2)\n2 - (4)\n3 - (1)\n4 - (3)"
        )

    with col2:
        st.subheader("2. Student Answer Sheet")
        student_file = st.file_uploader("Upload Student Answer Sheet (Image / OMR)", type=["jpg", "jpeg", "png"], key="student")
        if student_file:
            st.image(student_file, use_container_width=True)

    col_marks, col_per = st.columns(2)
    with col_marks:
        max_marks = st.number_input("Total Maximum Marks", value=50 if paper_type.startswith("MCQ") else 100)
    with col_per:
        marks_per_correct = st.number_input("Marks Per Correct Question", value=1, min_value=1) if paper_type.startswith("MCQ") else 1

    if st.button("Evaluate & Mark Paper (Uses 1 Credit)", type="primary", use_container_width=True):
        if credits <= 0:
            st.error("⚠️ ඔබගේ Credits ඉවර වී ඇත. කරුණාකර Sidebar එකෙන් Credits Buy කරන්න.")
        elif not scheme_file and not scheme_text:
            st.warning("කරුණාකර Marking Scheme එක ඇතුළත් කරන්න (Photo/PDF Upload කරන්න හෝ Text ලියන්න).")
        elif not student_file:
            st.warning("කරුණාකර ශිෂ්‍ය පිළිතුරු පත්‍රයේ Photo එකක් Upload කරන්න.")
        else:
            with st.spinner("AI Vision Model එක මගින් පිළිතුරු පත්‍රය පරීක්ෂා කරමින් පවතී..."):
                try:
                    contents = []
                    
                    if paper_type.startswith("MCQ"):
                        prompt = f"""
You are an expert Vision AI OMR and MCQ Answer Sheet Evaluator.
Perform a high-precision spatial and visual inspection of the uploaded student sheet against the correct answer scheme.

Evaluation Directives:
1. Extract and identify every question number on the student sheet and read the selected/marked answer (e.g., option 1, 2, 3, 4, 5 OR A, B, C, D, E or marked bubbles/crosses/circles/handwritten numbers).
2. Compare each detected student answer against the provided Correct Marking Scheme / Key.
3. Total Maximum Marks possible: {max_marks}. Marks allocated per correct answer: {marks_per_correct}.
4. Carefully inspect faint markings, circled choices, crossed options, or double markings (if double marked, mark as incorrect).

Formatting Output (Strictly format in Markdown with clear Sinhala & English section headings):

## 📊 MCQ Evaluation Summary
* **Total Questions Evaluated:** [Count]
* **Correct Answers (නිවැරදි පිළිතුරු):** [Count]
* **Incorrect / Unanswered (වැරදි / නොසපයන ලද):** [Count]
* **Final Score (ලබාගත් මුළු ලකුණු):** [Score] / {max_marks}

---

### 📝 Detailed Question Breakdown (ප්‍රශ්න පත්‍ර පරික්ෂාව)
Create a neat Markdown Table with the following columns:
| Q.No (ප්‍රශ්න අංකය) | Student Answer (සිසුවාගේ පිළිතුර) | Correct Answer (නිවැරදි පිළිතුර) | Status (තත්ත්වය) | Marks (ලකුණු) |

Rules for table rows:
- Status should be "✅ Correct" or "❌ Incorrect".
- Highlight any ambiguous/double answers clearly.

---

### 💡 Performance Analysis & Feedback (විශ්ලේෂණය සහ උපදෙස්)
- Provide brief constructive advice in Sinhala & English for topics/questions the student missed.
"""
                    else:
                        prompt = f"""
Evaluate this student essay/structured answer sheet against the provided marking scheme. 
Total Maximum Marks: {max_marks}

Provide:
1. Question-by-question breakdown.
2. Step marks & final score.
3. Detailed feedback in Sinhala & English.
"""

                    # 1. Attach Marking Scheme
                    if scheme_file:
                        if scheme_file.type == "application/pdf":
                            prompt += f"\nCorrect Marking Scheme Extracted from PDF:\n{pdf_extracted_text}\n"
                        else:
                            contents.append(Image.open(scheme_file))
                            prompt += "\nAttached Image 1: Correct Marking Scheme / Key Answer Sheet.\n"

                    if scheme_text:
                        prompt += f"\nAdditional Marking Scheme Rules / Key Answers:\n{scheme_text}\n"

                    # 2. Attach Student Answer Sheet
                    student_img = Image.open(student_file)
                    contents.append(student_img)
                    prompt += "\nAttached Image 2: Student Answer Sheet to be evaluated.\n"

                    contents.append(prompt)

                    response = generate_content_with_fallback(client, contents)

                    st.session_state.evaluation_result = response.text

                    deduct_credit(user_id, credits)
                    st.rerun()

                except Exception as e:
                    st.error(f"Error: {str(e)}")

    if st.session_state.evaluation_result:
        st.markdown("---")
        st.success("Paper Evaluation Completed!")
        st.markdown("### 📊 Evaluation Result & Feedback")
        st.markdown(st.session_state.evaluation_result)
