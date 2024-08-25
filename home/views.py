from django.shortcuts import render, redirect
from django.http import JsonResponse
from firebase_admin import firestore
import random
import uuid

db = firestore.client()

from random import choice

from random import choice
from django.utils import timezone
from datetime import datetime, time

def get_tip_of_the_day():
    today = timezone.now().date()
    daily_tip_doc_ref = db.collection('daily_tip').document(str(today))

    daily_tip_doc = daily_tip_doc_ref.get()
    
    if daily_tip_doc.exists:
        # If the document exists, return the stored tip of the day
        tip_id = daily_tip_doc.to_dict().get('tip_id')
        tip_doc = db.collection('tips').document(tip_id).get()
        return tip_doc.to_dict() if tip_doc.exists else None
    else:
        # No tip for today, select a random tip and store it
        all_tips_query = db.collection('tips').stream()
        all_tips = list(all_tips_query)
        
        if all_tips:
            selected_tip = random.choice(all_tips).to_dict()
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
        username = request.POST['username']
        twitter_username = request.POST.get('twitter_username', '')
        content = request.POST['content']
        
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

from django.http import JsonResponse

from django.views.decorators.http import require_POST
from django.views.decorators.csrf import csrf_protect

from django.views.decorators.http import require_POST
from django.views.decorators.csrf import csrf_protect

@require_POST
@csrf_protect
def toggle_reaction(request, tip_id, reaction_type):
    tip_ref = db.collection('tips').document(tip_id)
    tip = tip_ref.get()
    
    if tip.exists:
        liked_tips = request.session.get('liked_tips', [])
        disliked_tips = request.session.get('disliked_tips', [])
        
        if reaction_type == 'like':
            if tip_id in liked_tips:
                liked_tips.remove(tip_id)
                tip_ref.update({'likes': firestore.Increment(-1)})
            else:
                liked_tips.append(tip_id)
                tip_ref.update({'likes': firestore.Increment(1)})
                if tip_id in disliked_tips:
                    disliked_tips.remove(tip_id)
                    tip_ref.update({'dislikes': firestore.Increment(-1)})
        elif reaction_type == 'dislike':
            if tip_id in disliked_tips:
                disliked_tips.remove(tip_id)
                tip_ref.update({'dislikes': firestore.Increment(-1)})
            else:
                disliked_tips.append(tip_id)
                tip_ref.update({'dislikes': firestore.Increment(1)})
                if tip_id in liked_tips:
                    liked_tips.remove(tip_id)
                    tip_ref.update({'likes': firestore.Increment(-1)})
        
        request.session['liked_tips'] = liked_tips
        request.session['disliked_tips'] = disliked_tips
        
        # Fetch updated tip data
        updated_tip = tip_ref.get().to_dict()
        updated_tip['liked'] = tip_id in liked_tips
        updated_tip['disliked'] = tip_id in disliked_tips
        
        return JsonResponse(updated_tip)
    
    return JsonResponse({'error': 'Tip not found'}, status=404)
def get_tips(request, section):
    tips_ref = db.collection('tips')
    
    if section == 'feed':
        # Random selection of tips
        tips = list(tips_ref.get())
        random.shuffle(tips)
        tips = tips[:10]
    elif section == 'trending':
        # Most liked tips
        tips = tips_ref.order_by('likes', direction=firestore.Query.DESCENDING).limit(10).get()
    elif section == 'new':
        # Newly added tips
        tips = tips_ref.order_by('timestamp', direction=firestore.Query.DESCENDING).limit(10).get()
    
    liked_tips = request.session.get('liked_tips', [])
    disliked_tips = request.session.get('disliked_tips', [])
    
    tips_data = []
    for tip in tips:
        tip_dict = tip.to_dict()
        tip_dict['liked'] = tip_dict['id'] in liked_tips
        tip_dict['disliked'] = tip_dict['id'] in disliked_tips
        tips_data.append(tip_dict)
    
    return JsonResponse(tips_data, safe=False)