import json
import os
import time
import pandas as pd
import plotly.express as px
import streamlit as st

# Set Page Config
st.set_page_config(
    page_title="SafeBiteAllergyCompanion",
    layout="wide"
)

# ==============================================================================
# DEMO BACKEND / API SUBSTITUTE LAYER
# ==============================================================================

class MockSafeBiteAPI:
    """Simulates a live REST API for Streamlit Cloud deployment without needing Flask."""
    
    @staticmethod
    @st.cache_data
    def get_recipes():
        """Simulates GET /recipes endpoint."""
        if os.path.exists("recipes.json"):
            with open("recipes.json", "r", encoding="utf-8") as f:
                return json.load(f)
        return []

    @staticmethod
    def authenticate_user(username, password):
        """Simulates POST /users/authenticate endpoint."""
        if os.path.exists("users.json"):
            with open("users.json", "r", encoding="utf-8") as f:
                users = json.load(f)
                for u in users:
                    if u["username"] == username and u["password"] == password:
                        return {"authenticated": True, "user": u}
        return {"authenticated": False, "message": "Invalid credentials"}

    @staticmethod
    def add_recipe(new_recipe):
        """Simulates POST /recipes/add endpoint with session persistence."""
        # Update session state cache for active session
        recipes = st.session_state.get("cached_recipes", MockSafeBiteAPI.get_recipes())
        new_recipe["id"] = max([r.get("id", 0) for r in recipes], default=0) + 1
        recipes.append(new_recipe)
        st.session_state.cached_recipes = recipes
        return {"status": 201, "message": "Recipe added successfully", "recipe": new_recipe}

# Initialize in-memory dataset in session state
if "cached_recipes" not in st.session_state:
    st.session_state.cached_recipes = MockSafeBiteAPI.get_recipes()

# ==============================================================================
# AUTHENTICATION & SESSION STATE
# ==============================================================================
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
if "user_info" not in st.session_state:
    st.session_state.user_info = None

if not st.session_state.logged_in:
    st.title("SafeBiteAllergyCompanion")
    st.subheader("Please sign in to access personalized allergen filtering & metrics.")

    with st.form("login_form"):
        col1, col2 = st.columns(2)
        with col1:
            username_input = st.text_input("Username")
        with col2:
            password_input = st.text_input("Password", type="password")
        
        submit_button = st.form_submit_button("Login")

        if submit_button:
            response = MockSafeBiteAPI.authenticate_user(username_input, password_input)
            if response["authenticated"]:
                st.session_state.logged_in = True
                st.session_state.user_info = response["user"]
                st.success(f"Welcome back, {response['user']['name']}!")
                st.rerun()
            else:
                st.error("Invalid username or password. Try: student / password123")
    st.stop()

# ==============================================================================
# MAIN APPLICATION INTERFACE
# ==============================================================================

# Sidebar Navigation
st.sidebar.title(f"👤 {st.session_state.user_info['name']}")
if st.sidebar.button("Logout"):
    st.session_state.logged_in = False
    st.session_state.user_info = None
    st.rerun()

st.sidebar.markdown("---")
view_option = st.sidebar.radio(
    "Navigation Views",
    ["Recipe Explorer & Filter", "Allergen Data Analytics", "Add New Recipe (Mock POST Method)", "Feedback & Audit Form"]
)

# Fetch recipe dataset via Mock API Layer
recipes_data = st.session_state.cached_recipes
df = pd.DataFrame(recipes_data)

all_allergens = sorted(list(set([a for sublist in df['allergens'] for a in sublist]))) if 'allergens' in df.columns else []

# ------------------------------------------------------------------------------
# VIEW 1: RECIPE EXPLORER
# ------------------------------------------------------------------------------
if view_option == "Recipe Explorer & Filter":
    st.title("Safe Meal Explorer")
    st.caption("*Powered by Streamlit Cloud Native Backend Mock*")

    excluded_allergens = st.multiselect("Select Allergens to Exclude:", options=all_allergens, default=[])

    def is_safe(allergens_list):
        if not isinstance(allergens_list, list):
            return True
        return not any(a in excluded_allergens for a in allergens_list)

    df['is_safe'] = df['allergens'].apply(is_safe)
    safe_df = df[df['is_safe']].copy()

    m1, m2, m3 = st.columns(3)
    m1.metric("Total Dataset Items", len(df))
    m2.metric("Safe Recipes Available", len(safe_df))
    m3.metric("Excluded (Unsafe)", len(df) - len(safe_df))

    st.markdown("---")
    st.subheader(f"Available Safe Meals ({len(safe_df)})")
    
    if safe_df.empty:
        st.warning("No recipes match your current exclusion constraints.")
    else:
        for idx, row in safe_df.iterrows():
            allergens_str = ", ".join(row['allergens']) if row.get('allergens') else "None (Allergen Free)"
            with st.expander(f"{row['name']} — {row['category']} ({row.get('calories', 'N/A')} kcal)"):
                st.write(f"**Prep Time:** {row.get('prepTime', 'N/A')} minutes")
                st.write(f"**User Rating:** {row.get('rating', 'N/A')} / 5.0")
                st.write(f"**Flagged Allergens:** {allergens_str}")

# ------------------------------------------------------------------------------
# VIEW 2: DATA ANALYTICS
# ------------------------------------------------------------------------------
elif view_option == "Allergen Data Analytics":
    st.title("Dataset Analytics & Visualizations")
    col_chart1, col_chart2 = st.columns(2)

    with col_chart1:
        st.subheader("Allergen Prevalence Frequency")
        if 'allergens' in df.columns:
            allergen_counts = df.explode('allergens')['allergens'].value_counts().reset_index()
            allergen_counts.columns = ['Allergen', 'Count']
            
            fig1 = px.bar(allergen_counts, x='Allergen', y='Count', color='Count', color_continuous_scale='Reds')
            st.plotly_chart(fig1, use_container_width=True)

    with col_chart2:
        st.subheader("Calorie vs Prep Time Distribution")
        fig2 = px.scatter(df, x='prepTime', y='calories', color='category', size='rating', hover_name='name')
        st.plotly_chart(fig2, use_container_width=True)

# ------------------------------------------------------------------------------
# VIEW 3: ADD NEW RECIPE (MOCK POST CALL)
# ------------------------------------------------------------------------------
elif view_option == "Add New Recipe (Mock POST)":
    st.title("Add Custom Recipe to Dataset")
    st.caption("Demonstrates dynamic POST requests into session dataset.")

    with st.form("add_recipe_form"):
        rec_name = st.text_input("Recipe Name")
        category = st.selectbox("Category", ["Italian", "Asian", "Mexican", "Breakfast", "Vegan", "Dessert"])
        prep_time = st.number_input("Prep Time (mins)", min_value=1, value=15)
        calories = st.number_input("Calories (kcal)", min_value=50, value=300)
        selected_allergens = st.multiselect("Flagged Allergens", options=all_allergens)
        
        submitted = st.form_submit_button("Post Recipe to API")

        if submitted and rec_name:
            new_item = {
                "name": rec_name,
                "category": category,
                "prepTime": prep_time,
                "calories": calories,
                "rating": 5.0,
                "allergens": selected_allergens
            }
            res = MockSafeBiteAPI.add_recipe(new_item)
            st.success(f"Response {res['status']}: {res['message']}")
            st.rerun()

# ------------------------------------------------------------------------------
# VIEW 4: FEEDBACK FORM
# ------------------------------------------------------------------------------
elif view_option == "Feedback & Audit Form":
    st.title("Feedback & Audit Log")
    with st.form("contact_form"):
        name = st.text_input("Name", value=st.session_state.user_info['name'])
        feedback = st.text_area("Report an unflagged allergen:")
        if st.form_submit_button("Submit"):
            st.balloons()
            st.success("Feedback submitted!")