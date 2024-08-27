from django.shortcuts import render, redirect
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import csrf_protect
from django.core.exceptions import ValidationError
from django.utils import timezone
from firebase_admin import firestore
from html import escape
import random
import uuid
import re

db = firestore.client()

def sanitize_input(text):
    return escape(text)

def get_tip_of_the_day():
    today = timezone.now().date()
    daily_tip_doc_ref = db.collection('daily_tip').document(str(today))

    daily_tip_doc = daily_tip_doc_ref.get()
    
    if daily_tip_doc.exists:
        tip_id = daily_tip_doc.to_dict().get('tip_id')
        tip_doc = db.collection('tips').document(tip_id).get()
        tip = tip_doc.to_dict() if tip_doc.exists else None
        if tip and is_tip_safe(tip):
            return tip
    
    all_tips_query = db.collection('tips').limit(100).stream()  # Limit the query to improve performance
    safe_tips = [tip.to_dict() for tip in all_tips_query if is_tip_safe(tip.to_dict())]
    
    if safe_tips:
        selected_tip = random.choice(safe_tips)
        tip_id = selected_tip['id']
        
        daily_tip_doc_ref.set({'tip_id': tip_id})
        return selected_tip
    else:
        return None

def view_tips(request):
    tip_of_the_day = get_tip_of_the_day()
    return render(request, 'index.html', {'tip_of_the_day': tip_of_the_day})

def manage_tips(request):
    if request.method == 'POST':
        username = sanitize_input(request.POST['username'])
        twitter_username = sanitize_input(request.POST.get('twitter_username', ''))
        content = sanitize_input(request.POST['content'])
        
        if contains_suspicious_content(username) or contains_suspicious_content(twitter_username) or contains_suspicious_content(content):
            raise ValidationError("Suspicious content detected. Please remove any code or scripts from your input.")
        
        if len(content) > 280:
            raise ValidationError("Content exceeds maximum allowed length.")
        
        new_tip = {
            'id': str(uuid.uuid4()),
            'username': username,
            'twitter_username': twitter_username,
            'content': content,
            'likes': 0,
            'dislikes': 0,
            'timestamp': firestore.SERVER_TIMESTAMP
        }
        
        db.collection('tips').document(new_tip['id']).set(new_tip)
        
        return redirect('manage_tips')
    
    return view_tips(request)

@require_POST
@csrf_protect
def toggle_reaction(request, tip_id, reaction_type):
    tip_ref = db.collection('tips').document(tip_id)
    tip = tip_ref.get()
    
    if tip.exists:
        user_id = request.COOKIES.get('user_id', str(uuid.uuid4()))
        reaction_ref = db.collection('user_reactions').document(f"{user_id}_{tip_id}")
        reaction = reaction_ref.get()

        if reaction.exists:
            current_reaction = reaction.to_dict().get('reaction')
            
            if current_reaction == reaction_type:
                reaction_ref.delete()
                tip_ref.update({f"{reaction_type}s": firestore.Increment(-1)})
            else:
                reaction_ref.update({'reaction': reaction_type})
                tip_ref.update({
                    f"{current_reaction}s": firestore.Increment(-1),
                    f"{reaction_type}s": firestore.Increment(1)
                })
        else:
            reaction_ref.set({'reaction': reaction_type})
            tip_ref.update({f"{reaction_type}s": firestore.Increment(1)})

        updated_tip = tip_ref.get().to_dict()
        updated_tip['liked'] = reaction_type == 'like' if reaction.exists else False
        updated_tip['disliked'] = reaction_type == 'dislike' if reaction.exists else False
        response_data = {
            'likes': updated_tip['likes'],
            'dislikes': updated_tip['dislikes'],
            'liked': updated_tip['liked'],
            'disliked': updated_tip['disliked']
        }
        response = JsonResponse(response_data)
        if not request.COOKIES.get('user_id'):
            response.set_cookie('user_id', user_id, max_age=365*24*60*60)
        return response
    
    return JsonResponse({'error': 'Tip not found'}, status=404)

def contains_suspicious_content(text):
    suspicious_patterns = [
        r'<script',
        r'javascript:',
        r'onerror=',
        r'onclick=',
        r'onload=',
        r'<iframe',
        r'<button',
        r'document\.write',
        r'eval\(',
        r'alert\(',
        r'document\.cookie',
        r'document\.title',
        r'new Audio\(',
    ]
    return any(re.search(pattern, text, re.IGNORECASE) for pattern in suspicious_patterns)

def is_tip_safe(tip):
    return not (contains_suspicious_content(tip.get('content', '')) or 
                contains_suspicious_content(tip.get('username', '')))

def get_tips(request, section):
    tips_ref = db.collection('tips')
    
    if section == 'feed':
        # Use a more efficient method for random selection
        all_tips = list(tips_ref.limit(50).stream())  # Limit to 50 for better performance
        random.shuffle(all_tips)
        tips = all_tips[:10]  # Select the first 10 after shuffling
    elif section == 'trending':
        tips = tips_ref.order_by('likes', direction=firestore.Query.DESCENDING).limit(10).stream()
    elif section == 'new':
        tips = tips_ref.order_by('timestamp', direction=firestore.Query.DESCENDING).limit(10).stream()
    
    liked_tips = request.session.get('liked_tips', [])
    disliked_tips = request.session.get('disliked_tips', [])
    
    tips_data = []
    for tip in tips:
        tip_dict = tip.to_dict()
        if is_tip_safe(tip_dict):
            tip_dict['liked'] = tip_dict['id'] in liked_tips
            tip_dict['disliked'] = tip_dict['id'] in disliked_tips
            tips_data.append(tip_dict)
    
    return JsonResponse(tips_data, safe=False)

# New function to load initial feed
def load_initial_feed(request):
    return get_tips(request, 'feed')