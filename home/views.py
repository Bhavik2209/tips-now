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


from django.views.decorators.http import require_POST
from django.views.decorators.csrf import csrf_protect
import uuid

@require_POST
@csrf_protect
def toggle_reaction(request, tip_id, reaction_type):
    tip_ref = db.collection('tips').document(tip_id)
    tip = tip_ref.get()
    
    if tip.exists:
        # Get or create a unique identifier for the user
        user_id = request.COOKIES.get('user_id')
        if not user_id:
            user_id = str(uuid.uuid4())

        # Use a separate collection to store user reactions
        reaction_ref = db.collection('user_reactions').document(f"{user_id}_{tip_id}")
        reaction = reaction_ref.get()

        if reaction.exists:
            current_reaction = reaction.to_dict().get('reaction')
            
            if current_reaction == reaction_type:
                # User is toggling off their reaction
                reaction_ref.delete()
                tip_ref.update({f"{reaction_type}s": firestore.Increment(-1)})
            else:
                # User is changing their reaction
                reaction_ref.update({'reaction': reaction_type})
                tip_ref.update({
                    f"{current_reaction}s": firestore.Increment(-1),
                    f"{reaction_type}s": firestore.Increment(1)
                })
        else:
            # New reaction
            reaction_ref.set({'reaction': reaction_type})
            tip_ref.update({f"{reaction_type}s": firestore.Increment(1)})

        # Fetch updated tip data
        updated_tip = tip_ref.get().to_dict()
        updated_tip['liked'] = reaction_type == 'like' if reaction.exists else False
        updated_tip['disliked'] = reaction_type == 'dislike' if reaction.exists else False
        
        response = JsonResponse(updated_tip)
        if not request.COOKIES.get('user_id'):
            response.set_cookie('user_id', user_id, max_age=365*24*60*60)  # Set cookie to expire in 1 year
        return response
    
    return JsonResponse({'error': 'Tip not found'}, status=404)
    
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