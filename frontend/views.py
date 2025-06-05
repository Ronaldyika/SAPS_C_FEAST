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
    try:
        flyer_filename = 'flyer.png'
        flyer_path = os.path.join(settings.MEDIA_ROOT, flyer_filename)

        if not os.path.exists(flyer_path):
            raise FileNotFoundError(f"Flyer base image not found at {flyer_path}")

        base_img = Image.open(flyer_path).convert("RGBA")
        draw = ImageDraw.Draw(base_img)
        img_width, img_height = base_img.size
        center_x = img_width // 2

        def load_font(path, size):
            try:
                return ImageFont.truetype(path, size)
            except:
                # Fallback to a bold version of default font if specified font not found
                default_font = ImageFont.load_default()
                if "bd" in path.lower():  # If trying to load bold font
                    return ImageFont.load_default().font_variant(size=size, weight='bold')
                return ImageFont.load_default(size)

        # Load larger and bolder fonts
        name_font = load_font("arialbd.ttf", 60)  # Increased from 42 to 60
        role_font = load_font("arialbd.ttf", 48)  # Increased from 32 to 48 and made bold
        # time_font = load_font("arialbd.ttf", 28)  # Kept bold for consistency

        current_y = 140  # start near top for image

        # --- Add user image at top center ---
        if registration.image:
            try:
                with default_storage.open(registration.image.name) as img_file:
                    user_img = Image.open(img_file).convert("RGBA")
                    size = 400
                    user_img = user_img.resize((size, size))

                    mask = Image.new('L', (size, size), 0)
                    draw_mask = ImageDraw.Draw(mask)
                    draw_mask.ellipse((0, 0, size, size), fill=255)

                    circular_img = Image.new('RGBA', (size, size))
                    circular_img.paste(user_img, (0, 0), mask)

                    img_x = center_x - (size // 2)
                    base_img.paste(circular_img, (img_x, current_y), circular_img)
                    current_y += size + 40  # more spacing after image
            except Exception as e:
                print(f"Error loading user image: {e}")

        # --- Draw Name (larger, bold, with stroke) ---
        name_text = registration.name.upper()
        name_width = draw.textlength(name_text, font=name_font)
        name_position = (center_x - name_width // 2, current_y)
        draw.text(name_position, name_text, font=name_font, fill="white", stroke_width=3, stroke_fill="black")  # Increased stroke
        current_y += 75  # Increased spacing

        # --- Draw Role (larger, bold, with stroke) ---
        role_text = registration.role.upper()
        role_width = draw.textlength(role_text, font=role_font)
        role_position = (center_x - role_width // 2, current_y)
        draw.text(role_position, role_text, font=role_font, fill="yellow", stroke_width=3, stroke_fill="black")  # Increased stroke
        # Save flyer
        output_dir = os.path.join(settings.MEDIA_ROOT, 'generated_flyers')
        os.makedirs(output_dir, exist_ok=True)
        output_path = os.path.join(output_dir, f'flyer_{registration.id}.png')
        base_img.save(output_path, quality=95)

        return output_path

    except Exception as e:
        print(f"Error generating personalized flyer: {e}")
        raise

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