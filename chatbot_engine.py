import google.generativeai as genai
import os
import re
import uuid
from database import get_db_connection

class MuseumChatbot:
    def __init__(self):
        # Configure Gemini inside init to ensure env vars are loaded
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            print("ERROR: GEMINI_API_KEY not found in environment!")
        genai.configure(api_key=api_key)

        # We switch to a more stable model name to avoid the extremely low 20-request daily limit
        for model_name in ['gemini-2.0-flash', 'gemini-pro-latest', 'gemini-flash-latest']:
            try:
                self.model = genai.GenerativeModel(model_name)
                print(f"DEBUG: Using Gemini model: {model_name}")
                break
            except:
                continue
        self.booking_marker = "[INIT_BOOKING]"

    def _get_system_instructions(self):
        """Builds a dynamic context for the AI from the museum database."""
        conn = get_db_connection()
        exhibs = conn.execute('SELECT * FROM exhibitions').fetchall()
        conn.close()
        
        exhib_list = "\n".join([f"- {e['id']}. {e['title']} (₹{e['price']})" for e in exhibs])
        
        return f"""
        Role: You are 'Heritage Guru', the Virtual Curator. 
        Style: CONCISE. Keep responses brief (1-3 sentences) unless the user asks for detail.
        Language Rule: ALWAYS reply in the SAME LANGUAGE as the user. 
        
        Quick Info:
        - Hours: 9 AM-6 PM (Tue-Sun).
        - Location: North Civic Center, New Delhi.
        - Facilities: Cafe (2nd floor), Parking (North), 20% Student Discount.
        
        Current Exhibitions:
        {exhib_list}

        Interaction Rules: 
        1. Do NOT repeat the facility list or hours in every message.
        2. ONLY list the full exhibitions with prices when the user asks about tickets or booking.
        3. If the user is ready to book, explain how and MUST include the code '{self.booking_marker}' at the end.
        """

    def process_message(self, message, state_data):
        state = state_data.get('state', 'idle')
        
        # 1. Handle Numerical State Transitions (Selection & Count)
        if state == 'awaiting_exhibition_selection':
            match = re.search(r'\b\d+\b', message)
            if match:
                ex_id = int(match.group())
                conn = get_db_connection()
                exhibition = conn.execute('SELECT * FROM exhibitions WHERE id = ?', (ex_id,)).fetchone()
                conn.close()
                if exhibition:
                    state_data['exhibition'] = dict(exhibition)
                    state_data['state'] = 'awaiting_ticket_count'
                    return f"Great choice: {exhibition['title']}. How many tickets would you like to book?", state_data

        elif state == 'awaiting_ticket_count':
            match = re.search(r'\b\d+\b', message)
            if match:
                count = int(match.group())
                if count > 0:
                    state_data['count'] = count
                    state_data['state'] = 'awaiting_payment_confirm'
                    total = count * state_data['exhibition']['price']
                    state_data['total'] = total
                    btn_html = f"<div style='margin-top:10px;'><button class='cta-btn' onclick='openPaymentModal({total})'>Proceed to Ledger (₹{total})</button></div>"
                    return f"Confirming {count} tickets for '{state_data['exhibition']['title']}'. The total is ₹{total}. Shall we proceed?<br>{btn_html}", state_data

        # 2. Generative AI Logic
        try:
            instructions = self._get_system_instructions()
            response = self.model.generate_content(f"INSTRUCTIONS:\n{instructions}\n\nUSER MESSAGE: {message}")
            ai_text = response.text

            if self.booking_marker in ai_text:
                ai_text = ai_text.replace(self.booking_marker, "").strip()
                state_data['state'] = 'awaiting_exhibition_selection'
            
            if any(word in message.lower() for word in ['cancel', 'stop', 'restart', 'shuru']):
                state_data['state'] = 'idle'

            return ai_text, state_data
        
        except Exception as e:
            error_msg = str(e)
            print(f"Gemini Error (HYBRID FALLBACK TRIGGERED): {error_msg}")
            
            # --- BACKUP BRAIN (Rule-Based Fallback) ---
            msg = message.lower()
            
            # Greetings
            if re.search(r'\b(hi|hello|hey|namaste|greetings)\b', msg):
                return "Good day! I am the Virtual Curator. My AI brain is currently reaching its daily limit, but I can still help you with 'tickets', 'parking', 'hours', or 'history'.", state_data
            
            # Booking
            if re.search(r'\b(book|ticket|buy|reserve)\b', msg):
                state_data['state'] = 'awaiting_exhibition_selection'
                conn = get_db_connection()
                exhibs = conn.execute('SELECT * FROM exhibitions').fetchall()
                conn.close()
                resp = "I can definitely help with tickets. Reply with the number of your choice:<br>"
                for e in exhibs: resp += f"<b>{e['id']}. {e['title']}</b> - ₹{e['price']}<br>"
                return resp, state_data
                
            # Quick Info
            if 'hour' in msg or 'time' in msg or 'open' in msg:
                return "Museum Hours: 9:00 AM - 6:00 PM (Tue-Sun). Closed Mondays.", state_data
            if 'park' in msg or 'car' in msg or 'vehic' in msg:
                return "We have valet parking available in the North Wing. It is free for visitors.", state_data
            if 'cafe' in msg or 'food' in msg or 'eat' in msg:
                return "The Curator's Cafe is on the 2nd floor, open until 5 PM.", state_data
            if 'secur' in msg or 'safe' in msg:
                return "Security is our priority with 24/7 CCTV and entry screening. Flash photography is prohibited.", state_data
            
            return "I apologize, my AI brain is currently over-taxed (Quota Exceeded). However, you can still ask me about 'tickets', 'timings', 'parking', or 'cafe' and I will assist you!", state_data

    def process_payment_success(self, state_data, user_id):
        ticket_hash = str(uuid.uuid4())[:8].upper()
        
        conn = get_db_connection()
        conn.execute(
            'INSERT INTO bookings (user_id, visitor_name, exhibition_id, num_tickets, total_price, ticket_hash) VALUES (?, ?, ?, ?, ?, ?)',
            (user_id, 'Heritage Guest', state_data['exhibition']['id'], state_data['count'], state_data['total'], ticket_hash)
        )
        conn.commit()
        conn.close()
        
        state_data['state'] = 'idle'
        return {'success': True, 'chat_message': f"Payment Successful! 🎉<br>Booking ID: {ticket_hash}<br>Enjoy your visit to the museum!"}, state_data
