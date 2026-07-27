import os
import streamlit as st
import google.genai as genai
from PIL import Image

st.set_page_config(page_title="AI Paper Marker", page_icon="📝")
st.title("📝 School AI Paper Marking Platform")

# Retrieve API Key securely from secrets
api_key = st.secrets.get("GEMINI_API_KEY", os.environ.get("GEMINI_API_KEY"))

if not api_key:
    st.error("GEMINI_API_KEY එක සෙට් කර නොමැත. Secrets වලට එකතු කරන්න.")
    st.stop()

client = genai.Client(api_key=api_key)

uploaded_file = st.file_uploader("Upload Student Answer Sheet (JPG/PNG)", type=["jpg", "jpeg", "png"])
marking_scheme = st.text_area("Marking Scheme / Model Answers", height=150)
max_marks = st.number_input("Total Maximum Marks", value=100)

if st.button("Evaluate & Mark Paper", type="primary"):
    if uploaded_file and marking_scheme:
        with st.spinner("AI මගින් පත්‍රය පරීක්ෂා කරමින් පවතී..."):
            image = Image.open(uploaded_file)
            prompt = f"""
            You are an expert school exam evaluator.
            Analyze the attached student answer sheet image against the provided marking scheme/rubrics.

            ### Marking Scheme / Correct Answers:
            {marking_scheme}

            ### Maximum Marks:
            {max_marks}

            ### Tasks:
            1. Evaluate each question step-by-step.
            2. Point out specific errors, missing steps, or misconceptions.
            3. Award marks based on the scheme.
            4. Provide feedback in clear Sinhala or English (as suitable for Sri Lankan school students).

            ### Output Format:
            - **Question Breakdown**: (Marks per question)
            - **Total Score**: X / {max_marks}
            - **Key Feedback & Corrections**:
            """

            try:
                response = client.models.generate_content(
                    model='gemini-2.5-flash',
                    contents=[image, prompt]
                )
                st.markdown("### Evaluation Result")
                st.write(response.text)
            except Exception as e:
                st.error(f"Error: {str(e)}")
    else:
        st.warning("කරුණාකර Image එක සහ Marking Scheme එක ලබාදෙන්න.")
