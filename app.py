import os
import streamlit as st
import google.genai as genai
import urllib.parse
from PIL import Image
from supabase import create_client, Client

st.set_page_config(page_title="AI Paper Marker Pro", page_icon="📝", layout="wide")

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
    st.sidebar.write("රු. 1,000/= (Credits 1000)")
    
    PAYHERE_MERCHANT_ID = st.secrets.get("PAYHERE_MERCHANT_ID", "123456")
    payhere_url = f"https://www.payhere.lk/pay/checkout?merchant_id={PAYHERE_MERCHANT_ID}&items=Paper+Marking+100+Credits&amount=1000&currency=LKR&custom_1={user_id}"
    
    st.sidebar.markdown(f"[👉 Pay via PayHere (Card / eZ Cash)]({payhere_url})", unsafe_allow_html=True)

    # --- WHATSAPP RECEIPT BUTTON ---
    whatsapp_number = "94712382306"
    whatsapp_msg = f"Hello! I made a payment for AI Paper Marker Credits.\n\nUser Email: {user_email}\nUser ID: {user_id}\n\nPlease find my attached payment receipt/slip."
    encoded_msg = urllib.parse.quote(whatsapp_msg)
    whatsapp_url = f"https://wa.me/{whatsapp_number}?text={encoded_msg}"

    st.sidebar.markdown(
        f'''
        <a href="{whatsapp_url}" target="_blank" style="text-decoration: none;">
            <div style="
                background-color: #25D366;
                color: white;
                padding: 10px;
                border-radius: 8px;
                text-align: center;
                font-weight: bold;
                margin-top: 10px;
                margin-bottom: 10px;">
                💬 WhatsApp හරහා Slip එක එවන්න
            </div>
        </a>
        ''',
        unsafe_allow_html=True
    )

    if st.sidebar.button("Logout"):
        st.session_state.user = None
        st.session_state.evaluation_result = None
        st.rerun()

# --- MAIN APPLICATION ---
st.title("📝 School AI Paper Marking Platform")

if not st.session_state.user:
    st.info("👋 Platform එක භාවිත කිරීමට කරුණාකර Sidebar එකෙන් Login වන්න හෝ නොමිලේ Account එකක් සාදාගන්න (Free 5 Credits ලැබෙනු ඇත).")
else:
    user_id = st.session_state.user.id
    credits = get_user_credits(user_id)

    col1, col2 = st.columns(2)

    with col1:
        st.subheader("1. Student Answer Sheet")
        student_file = st.file_uploader("Upload Student Answer Sheet", type=["jpg", "jpeg", "png"], key="student")
        if student_file:
            st.image(student_file, use_container_width=True)

    with col2:
        st.subheader("2. Marking Scheme")
        scheme_file = st.file_uploader("Upload Marking Scheme Image", type=["jpg", "jpeg", "png"], key="scheme")
        if scheme_file:
            st.image(scheme_file, use_container_width=True)
        scheme_text = st.text_area("Or Type Marking Scheme", height=100)

    max_marks = st.number_input("Total Maximum Marks", value=100)

    if st.button("Evaluate & Mark Paper (Uses 1 Credit)", type="primary", use_container_width=True):
        if credits <= 0:
            st.error("⚠️ ඔබගේ Credits ඉවර වී ඇත. කරුණාකර Sidebar එකෙන් Credits Buy කරන්න.")
        elif not student_file:
            st.warning("කරුණාකර ශිෂ්‍ය පිළිතුරු පත්‍රයේ Photo එකක් Upload කරන්න.")
        elif not scheme_file and not scheme_text:
            st.warning("කරුණාකර Marking Scheme එක ඇතුළත් කරන්න.")
        else:
            with st.spinner("AI මගින් පත්‍රය විශ්ලේෂණය කරමින් පවතී..."):
                try:
                    student_img = Image.open(student_file)
                    contents = [student_img]

                    prompt = f"Evaluate this student answer sheet against the marking scheme. Maximum Marks: {max_marks}\n"

                    if scheme_file:
                        contents.append(Image.open(scheme_file))
                        prompt += "Attached is the marking scheme image.\n"
                    if scheme_text:
                        prompt += f"Marking Rules: {scheme_text}\n"

                    prompt += "Provide question breakdown, total score, and detailed Sinhala/English feedback."
                    contents.append(prompt)

                    response = client.models.generate_content(
                        model='gemini-2.5-flash',
                        contents=contents
                    )

                    # Store result persistently
                    st.session_state.evaluation_result = response.text

                    # Deduct credit
                    deduct_credit(user_id, credits)
                    st.rerun()

                except Exception as e:
                    st.error(f"Error: {str(e)}")

    # Display evaluation result persistently
    if st.session_state.evaluation_result:
        st.markdown("---")
        st.success("Paper Evaluation Completed!")
        st.markdown("### 📊 Evaluation Result & Feedback")
        st.markdown(st.session_state.evaluation_result)
