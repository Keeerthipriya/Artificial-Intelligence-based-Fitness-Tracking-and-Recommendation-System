# from urllib import response

from flask import Flask, render_template, request, redirect, url_for, session, send_file
import firebase_admin
from firebase_admin import credentials, firestore
# from google.generativeai import GenerativeModel
# import google.generativeai as genai
from google import genai
from datetime import datetime
import pandas as pd
import plotly.express as px
import os
from dotenv import load_dotenv
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from io import BytesIO
from pdf import create_fitness_plan_pdf, create_meal_plan_pdf
# Load environment variables from .env
load_dotenv()

# Initialize Flask
app = Flask(__name__)
app.secret_key = 'your_secret_key'  # Change this to a secure secret key

# Initialize Firebase (only if not already initialized)
if not firebase_admin._apps:
    cred = credentials.Certificate('./fit-tracker.json')
    firebase_admin.initialize_app(cred)

# Initialize Firestore
db = firestore.client()

# Set up Gemini API using the GOOGLE_API_KEY from the .env file
GOOGLE_API_KEY = os.getenv('GOOGLE_API_KEY')
if not GOOGLE_API_KEY:
    raise Exception("GOOGLE_API_KEY not found in environment variables")
# genai.configure(api_key=GOOGLE_API_KEY)
client = genai.Client(api_key=GOOGLE_API_KEY)
SAFE_DEFAULT_GENAI_MODEL = 'gemini-flash-lite-latest'
USER_GENAI_MODEL = os.getenv('GENAI_MODEL')
MODEL_FALLBACKS = [
    SAFE_DEFAULT_GENAI_MODEL,
    'gemini-flash-latest',
    'gemini-pro-latest',
    'gemini-2.5-flash',
    'gemini-2.5-pro'
]
if USER_GENAI_MODEL:
    MODEL_FALLBACKS.append(USER_GENAI_MODEL)
MODEL_FALLBACKS = list(dict.fromkeys(MODEL_FALLBACKS))
DEFAULT_GENAI_MODEL = USER_GENAI_MODEL or SAFE_DEFAULT_GENAI_MODEL

@app.route('/')
def home():
    return render_template('home.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        confirm_password = request.form['confirm_password']
        
        if password != confirm_password:
            return render_template('register.html', error="Passwords do not match")
        
        # Check if username exists
        users_ref = db.collection('users')
        query = users_ref.where('username', '==', username).limit(1)
        
        if len(list(query.stream())) > 0:
            return render_template('register.html', error="Username already exists")
        
        try:
            # Create new user
            new_user = users_ref.document()
            new_user.set({
                'username': username,
                'password': password,  # In production, use proper password hashing
                'created_at': firestore.SERVER_TIMESTAMP
            })
            
            # Set session
            session['user_id'] = new_user.id
            return redirect(url_for('profile'))
            
        except Exception as e:
            return render_template('register.html', error=f"Registration failed: {str(e)}")
    
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        users_ref = db.collection('users')
        query = users_ref.where('username', '==', username).where('password', '==', password).limit(1)
        
        users = list(query.stream())
        if users:
            session['user_id'] = users[0].id
            return redirect(url_for('profile'))
        
        return render_template('login.html', error="Invalid credentials")
    
    return render_template('login.html')
# Add this route after the login route

@app.route('/logout')
def logout():
    session.pop('user_id', None)  # Remove user_id from session
    return redirect(url_for('login'))

@app.route('/profile')
def profile():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    user_doc = db.collection('user_details').document(session['user_id']).get()
    user_data = {}
    
    if user_doc.exists:
        user_data = user_doc.to_dict()
    
    # Get recent progress
    progress_ref = db.collection('progress')
    recent_progress = progress_ref.where('user_id', '==', session['user_id']).order_by('date', direction=firestore.Query.DESCENDING).limit(5).stream()
    
    progress_list = []
    for doc in recent_progress:
        data = doc.to_dict()
        progress_list.append({
            'id': doc.id,  # Add this line to include the document ID
            'date': data['date'].strftime('%Y-%m-%d'),
            'weight': data['weight'],
            'calories_eaten': data['calories_eaten'],
            'workout_completed': data['workout_completed']
        })
    
    return render_template('profile.html', user_data=user_data, progress=progress_list)

@app.route('/delete_progress/<entry_id>', methods=['POST'])
def delete_progress(entry_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))
        
    try:
        # Check if the progress entry belongs to the current user
        progress_ref = db.collection('progress').document(entry_id)
        progress_doc = progress_ref.get()
        
        if progress_doc.exists and progress_doc.to_dict()['user_id'] == session['user_id']:
            progress_ref.delete()
            
    except Exception as e:
        print(f"Error deleting progress entry: {e}")
        
    return redirect(url_for('profile'))


@app.route('/edit_profile', methods=['GET', 'POST'])
def edit_profile():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    if request.method == 'POST':
        user_details = {
            'user_id': session['user_id'],
            'name': request.form['name'],
            'age': int(request.form['age']),
            'height': float(request.form['height']),
            'weight': float(request.form['weight']),
            'work_type': request.form['work_type'],
            'goal': request.form['goal'],
            'current_calories': int(request.form['current_calories']),
            'workout_split': request.form['workout_split'],
            'updated_at': firestore.SERVER_TIMESTAMP
        }
        
        db.collection('user_details').document(session['user_id']).set(user_details)
        
        # Generate workout plan
        plan = generate_workout_plan(user_details)
        db.collection('user_details').document(session['user_id']).update({
            'plan': plan
        })
        
        return redirect(url_for('profile'))
    
    # Get existing user details
    user_doc = db.collection('user_details').document(session['user_id']).get()
    user_data = user_doc.to_dict() if user_doc.exists else {}
    
    return render_template('edit_profile.html', user_data=user_data)



@app.route('/view_plan')
def view_plan():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    user_doc = db.collection('user_details').document(session['user_id']).get()
    
    if user_doc.exists:
        user_data = user_doc.to_dict()
        plan = user_data.get('plan', 'No plan generated yet.')
        return render_template('plan.html', plan=plan)
    else:
        return redirect(url_for('profile'))

@app.route('/progress', methods=['GET', 'POST'])
def progress():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    if request.method == 'POST':
        progress_data = {
            'user_id': session['user_id'],
            'date': datetime.now(),
            'weight': float(request.form['weight']),
            'calories_eaten': int(request.form['calories_eaten']),
            'workout_completed': request.form['workout_completed'],
            'created_at': firestore.SERVER_TIMESTAMP
        }
        
        db.collection('progress').add(progress_data)
        return redirect(url_for('analyze'))
    
    return render_template('progress.html', current_date=datetime.now())
@app.route('/analyze')
def analyze():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    progress_ref = db.collection('progress')
    query = progress_ref.where('user_id', '==', session['user_id']).order_by('date')
    
    progress_data = []
    dates = []
    weights = []
    calories = []
    
    for doc in query.stream():
        data = doc.to_dict()
        dates.append(data['date'].strftime('%b %d'))
        weights.append(data['weight'])
        calories.append(data['calories_eaten'])
        progress_data.append(data)
    
    stats = {
        'total_workouts': len(progress_data),
        'weight_change': weights[-1] - weights[0] if weights else 0,
        'avg_calories': sum(calories) / len(calories) if calories else 0
    }
    
    return render_template('analyze.html',
                         stats=stats,
                         dates=dates,
                         weights=weights,
                         calories=calories)
@app.route('/download_plan')
def download_plan():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    user_doc = db.collection('user_details').document(session['user_id']).get()
    
    if not user_doc.exists:
        return "No plan found", 404
    
    user_data = user_doc.to_dict()
    plan = user_data.get('plan', 'No plan available')
    
    # Use the enhanced PDF generator
    buffer = create_fitness_plan_pdf(user_data, plan)
    
    return send_file(
        buffer,
        download_name='FitTracker_Workout_Plan.pdf',
        as_attachment=True,
        mimetype='application/pdf'
    )
    

def extract_generated_text(response):
    if hasattr(response, 'text') and response.text:
        return response.text
    if hasattr(response, 'candidates') and response.candidates:
        first = response.candidates[0]
        content = getattr(first, 'content', None)
        if content:
            if hasattr(content, 'parts'):
                return ''.join(getattr(part, 'text', '') for part in content.parts)
            return getattr(content, 'text', '')
    return ''


def generate_content_with_fallback(prompt):
    for model_name in MODEL_FALLBACKS:
        try:
            print(f"Trying model: {model_name}")
            response = client.models.generate_content(
                model=model_name,
                contents=prompt
            )
            generated_text = extract_generated_text(response)
            if generated_text:
                return generated_text
            print(f"Warning: no text returned from model {model_name}")
        except Exception as e:
            error_text = str(e).lower()
            print(f"Error generating content with {model_name}: {str(e)}")
            if any(token in error_text for token in ['resource_exhausted', 'quota', '429', 'not_found', 'unsupported', 'invalid', 'bad request', '400']):
                continue
            print(f"Unhandled generation error with {model_name}, continuing to next model")
            continue
    print("All Gemini model attempts failed, returning None to use fallback plan")
    return None


def generate_workout_plan(user_details):
    try:
        prompt = f"""
        Create a detailed workout plan for someone with the following characteristics:
        - Height: {user_details.get('height')} cm
        - Weight: {user_details.get('weight')} kg
        - Activity Level: {user_details.get('work_type')}
        - Fitness Goal: {user_details.get('goal')}
        - Daily Calorie Target: {user_details.get('current_calories')}
        - Preferred Workout Split: {user_details.get('workout_split')}

        Please provide a comprehensive plan that includes:
        1. Weekly schedule breakdown
        2. Specific exercises for each day
        3. Sets and reps for each exercise
        4. Rest periods
        5. Nutrition recommendations
        6. Progress tracking tips
        """

        # model = GenerativeModel('gemini-1.5-flash')
        # response = model.generate_content(prompt)
        generated_text = generate_content_with_fallback(prompt)
        return generated_text or generate_fallback_plan(user_details)

    except Exception as e:
        print(f"Error generating workout plan: {str(e)}")
        return generate_fallback_plan(user_details)

def generate_fallback_plan(user_details):
    return f"""
    BASIC WORKOUT PLAN (Fallback)
    
    Goal: {user_details.get('goal')}
    Split: {user_details.get('workout_split')}
    
    Weekly Schedule:
    Monday: Upper Body
    - Bench Press: 3x8-12
    - Shoulder Press: 3x8-12
    - Rows: 3x8-12
    
    Wednesday: Lower Body
    - Squats: 3x8-12
    - Deadlifts: 3x8-12
    - Lunges: 3x8-12
    
    Friday: Full Body
    - Pull-ups: 3x8-12
    - Push-ups: 3x8-12
    - Leg Press: 3x8-12
    
    Daily Calorie Target: {user_details.get('current_calories')}
    """

def generate_fallback_meal_plan(user_details, diet_preference, allergies):
    return f"""
    BASIC MEAL PLAN (Fallback)
    Diet Preference: {diet_preference}
    Allergies / Additional Info: {allergies}
    Daily Calorie Target: {user_details.get('current_calories')}

    Breakfast:
    - Oatmeal with fruits and nuts

    Lunch:
    - Grilled chicken or tofu with mixed vegetables and brown rice

    Dinner:
    - Baked fish or lentils with steamed greens

    Snacks:
    - Greek yogurt, fruit, or a handful of nuts
    """
# Update the generate_meal_plan function to accept diet_preference and allergies
def generate_meal_plan(user_details, diet_preference, allergies):
    try:
        prompt = f"""
        Create a detailed meal plan for an athlete with these details:
        - Diet Preference: {diet_preference}
        - Allergies / Additional Info: {allergies}
        - Height: {user_details.get('height')} cm
        - Weight: {user_details.get('weight')} kg
        - Activity Level: {user_details.get('work_type')}
        - Fitness Goal: {user_details.get('goal')}
        - Daily Calorie Target: {user_details.get('current_calories')}
        
        Provide a comprehensive meal plan including:
        1. Breakfast, Lunch, Dinner, and Snacks
        2. Specific foods with portion sizes and nutritional info
        3. Timing and preparation tips
        4. Healthy substitutions and variety

          Format STRICTLY like this:

        Breakfast:
        - Item with portion

        Lunch:
        - Item with portion

        Dinner:
        - Item with portion

        Snacks:
        - Item with portion

        Keep it simple. Avoid long paragraphs.
        """
        # model = GenerativeModel('gemini-1.5-flash')
        # response = model.generate_content(prompt)
        generated_text = generate_content_with_fallback(prompt)
        return generated_text or generate_fallback_meal_plan(user_details, diet_preference, allergies)
    except Exception as e:
        print(f"Error generating meal plan: {str(e)}")
        return generate_fallback_meal_plan(user_details, diet_preference, allergies)

# Update the meal_suggester route to send these new details
@app.route('/meal_suggester', methods=['GET', 'POST'])
def meal_suggester():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    user_doc = db.collection('user_details').document(session['user_id']).get()
    if not user_doc.exists:
        return redirect(url_for('edit_profile'))
    user_data = user_doc.to_dict()
    
    if request.method == 'POST':
        try:
            diet_pref = request.form.get('diet_preference', 'veg')
            allergies = request.form.get('allergies', '')
            
            # Store preferences in database
            db.collection('user_details').document(session['user_id']).update({
                'diet_preference': diet_pref,
                'allergies': allergies,
                'updated_at': firestore.SERVER_TIMESTAMP
            })
            
            # Generate meal plan
            meal_plan_text = generate_meal_plan(user_data, diet_pref, allergies)
            
            # Store the meal plan
            db.collection('user_details').document(session['user_id']).update({
                'meal_plan': meal_plan_text
            })
            
            return redirect(url_for('meal_suggester'))
        
        except Exception as e:
            print(f"Error generating meal plan: {str(e)}")
            return redirect(url_for('meal_suggester', error='generation_failed'))
    
    return render_template('meal_suggester.html', user_data=user_data)

@app.route('/download_meal_plan')
def download_meal_plan():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    user_doc = db.collection('user_details').document(session['user_id']).get()
    if not user_doc.exists:
        return "No meal plan found", 404
    
    user_data = user_doc.to_dict()
    meal_plan = user_data.get('meal_plan')
    
    if not meal_plan:
        return "No meal plan available", 404
    
    # Generate PDF
    pdf_buffer = create_meal_plan_pdf(meal_plan, user_data)
    
    return send_file(
        pdf_buffer,
        download_name='FitTracker_Meal_Plan.pdf',
        as_attachment=True,
        mimetype='application/pdf'
    )

if __name__ == '__main__':
    app.run(debug=True)
