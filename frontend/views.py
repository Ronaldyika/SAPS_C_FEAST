from django.shortcuts import render, redirect
from django.http import HttpResponse
from django.core.paginator import Paginator
from .models import Attendee
from PIL import Image, ImageDraw, ImageFont, ImageOps
import os
from django.conf import settings
from .forms import ConcertRegistrationForm
from .models import Attendee
from django.templatetags.static import static
from django.core.files.storage import default_storage
from django.contrib import messages

from django.urls import reverse

def concert_registration_view(request):
    if request.method == 'POST':
        form = ConcertRegistrationForm(request.POST, request.FILES)
        if form.is_valid():
            try:
                registration = form.save()
                
                flyer_path = generate_personalized_flyer(registration)

                # Save relative path
                registration.generated_flyer.name = flyer_path.replace(str(settings.MEDIA_ROOT) + '/', '')
                registration.save()

                # Redirect to the flyer preview page
                return redirect(reverse('flyer_preview', args=[registration.id]))

            except Exception as e:
                print(f"Error generating flyer: {e}")
                messages.error(request, 'There was an error generating your flyer. Please try again.')
                return render(request, 'index.html', {'form': form})
    else:
        form = ConcertRegistrationForm()

    return render(request, 'index.html', {'form': form})
def generate_personalized_flyer(registration):
    static_image_path = os.path.join('image', 'flyer.png')
    base_flyer_path = os.path.join(settings.BASE_DIR, 'static', static_image_path)

    if hasattr(settings, 'STATIC_ROOT') and settings.STATIC_ROOT:
        alt_path = os.path.join(settings.STATIC_ROOT, static_image_path)
        if os.path.exists(alt_path):
            base_flyer_path = alt_path

    if not os.path.exists(base_flyer_path):
        raise FileNotFoundError(f"Flyer not found at {base_flyer_path}")

    base_img = Image.open(base_flyer_path).convert('RGBA')
    draw = ImageDraw.Draw(base_img)
    img_width, img_height = base_img.size
    center_x = img_width // 2

    # Use Google Fonts (Poppins-Bold)
    font_dir = os.path.join(settings.BASE_DIR, 'static', 'fonts')
    font_path = os.path.join(font_dir, 'Poppins-Bold.ttf')  # Ensure this file exists

    try:
        name_font = ImageFont.truetype(font_path, 80)
        role_font = ImageFont.truetype(font_path, 65)
    except Exception as e:
        print(f"Font loading error: {e}")
        name_font = ImageFont.load_default()
        role_font = ImageFont.load_default()

    top_padding = 40
    text_padding = 30

    if registration.image:
        try:
            with default_storage.open(registration.image.name) as img_file:
                user_img = Image.open(img_file).convert("RGBA")
                size = 350
                user_img = user_img.resize((size, size))

                mask = Image.new('L', (size, size), 0)
                draw_mask = ImageDraw.Draw(mask)
                draw_mask.ellipse((0, 0, size, size), fill=255)

                circular_img = Image.new('RGBA', (size, size))
                circular_img.paste(user_img, (0, 0), mask)

                img_x = center_x - (size // 2)
                img_y = top_padding
                base_img.paste(circular_img, (img_x, img_y), circular_img)

                text_start_y = img_y + size + text_padding
        except Exception as e:
            print(f"Image processing error: {e}")
            text_start_y = top_padding + 350 + text_padding
    else:
        text_start_y = top_padding

    # Draw role
    role_text = registration.role.upper()
    role_width = draw.textlength(role_text, font=role_font)
    role_x = center_x - role_width // 2
    draw.text((role_x, text_start_y), role_text, fill="white", font=role_font)

    # Draw name
    name_y = text_start_y + role_font.size + text_padding
    name_text = registration.name.upper()
    name_width = draw.textlength(name_text, font=name_font)
    name_x = center_x - name_width // 2
    draw.text((name_x, name_y), name_text, fill="white", font=name_font)

    output_dir = os.path.join(settings.MEDIA_ROOT, 'generated_flyers')
    os.makedirs(output_dir, exist_ok=True)
    output_path = os.path.join(output_dir, f'flyer_{registration.id}.png')
    base_img.save(output_path)

    return output_path


def flyer_preview_view(request, pk):
    try:
        attendee = Attendee.objects.get(pk=pk)
        return render(request, 'flyer_preview.html', {'attendee': attendee})
    except Attendee.DoesNotExist:
        messages.error(request, "Flyer not found.")
        return redirect('index')

def attendee_list(request):
    # Get all attendees ordered by creation date (newest first)
    attendees_list = Attendee.objects.all().order_by('-created_at')
    
    # Paginate the attendees (10 per page)
    paginator = Paginator(attendees_list, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'attendees': page_obj,
        'page_obj': page_obj,  # For pagination controls
        'is_paginated': paginator.num_pages > 1  # Show pagination only if needed
    }
    return render(request, 'list.html', context)
