import os
import streamlit as st
import google.genai as genai
from PIL import Image

st.set_page_config(page_title="AI Paper Marker", page_icon="📝", layout="wide")
st.title("📝 School AI Paper Marking Platform")
st.write("ශිෂ්‍ය පිළිතුරු පත්‍රය සහ Marking Scheme එක Image/Photo ලෙස upload කර AI මගින් ඇගයීම සිදුකරන්න.")

# Retrieve API Key securely from Streamlit secrets
api_key = st.secrets.get("GEMINI_API_KEY", os.environ.get("GEMINI_API_KEY"))

if not api_key:
    st.error("GEMINI_API_KEY එක සෙට් කර නොමැත. Secrets වලට එකතු කරන්න.")
    st.stop()

client = genai.Client(api_key=api_key)

col1, col2 = st.columns(2)

with col1:
    st.subheader("1. Student Answer Sheet")
    student_file = st.file_uploader(
        "Upload Student Answer Sheet (JPG/PNG)", 
        type=["jpg", "jpeg", "png"],
        key="student"
    )
    if student_file:
        st.image(student_file, caption="Student Answer Sheet", use_container_width=True)

with col2:
    st.subheader("2. Marking Scheme / Answer Key")
    # Marking scheme upload as Image or Text option
    scheme_file = st.file_uploader(
        "Upload Marking Scheme Image (JPG/PNG)", 
        type=["jpg", "jpeg", "png"],
        key="scheme"
    )
    if scheme_file:
        st.image(scheme_file, caption="Marking Scheme Image", use_container_width=True)
    
    scheme_text = st.text_area(
        "Or Type/Paste Marking Scheme (Optional if image uploaded)", 
        height=100
    )

max_marks = st.number_input("Total Maximum Marks", value=100)

if st.button("Evaluate & Mark Paper", type="primary", use_container_width=True):
    if not student_file:
        st.warning("කරුණාකර ශිෂ්‍ය පිළිතුරු පත්‍රයේ Photo එකක් Upload කරන්න.")
    elif not scheme_file and not scheme_text:
        st.warning("කරුණාකර Marking Scheme එක Image එකක් ලෙස Upload කරන්න හෝ Text ලෙස ඇතුළත් කරන්න.")
    else:
        with st.spinner("AI මගින් පත්‍ර දෙකම විශ්ලේෂණය කරමින් පවතී..."):
            try:
                # Prepare inputs for Gemini
                student_img = Image.open(student_file)
                contents = [student_img]

                prompt = f"""
                You are an expert school exam paper evaluator.
                Analyze the provided student answer sheet image against the given marking scheme.
                
                ### Maximum Marks for Paper: {max_marks}

                """

                if scheme_file:
                    scheme_img = Image.open(scheme_file)
                    contents.append(scheme_img)
                    prompt += "\nNote: I have attached the Marking Scheme as an image as well. Compare the student's answer image with the marking scheme image."
                
                if scheme_text:
                    prompt += f"\nAdditional Marking Rules/Scheme Text:\n{scheme_text}"

                prompt += """
                ### Evaluation Tasks:
                1. Evaluate each question step-by-step.
                2. Point out specific errors, missing steps, or misconceptions.
                3. Award marks based on the scheme.
                4. Provide constructive feedback in clear Sinhala or English (suited for Sri Lankan students).

                ### Output Format:
                - **Question Breakdown**: (Marks per question)
                - **Total Score**: X / {max_marks}
                - **Key Feedback & Corrections**:
                """

                contents.append(prompt)

                # Call Gemini API
                response = client.models.generate_content(
                    model='gemini-2.5-flash',
                    contents=contents
                )

                st.markdown("---")
                st.markdown("### 📊 Evaluation Result & Feedback")
                st.markdown(response.text)

            except Exception as e:
                st.error(f"Error during evaluation: {str(e)}")
