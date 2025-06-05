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


import os
from PIL import Image, ImageDraw, ImageFont
from django.conf import settings
from django.core.files.storage import default_storage
import logging

logger = logging.getLogger(__name__)

def generate_personalized_flyer(registration):
    try:
        # Predefined constants
        FLYER_FILENAME = 'flyer.png'
        OUTPUT_DIR = os.path.join(settings.MEDIA_ROOT, 'generated_flyers')
        
        # Cache paths and directories
        flyer_path = os.path.join(settings.MEDIA_ROOT, FLYER_FILENAME)
        os.makedirs(OUTPUT_DIR, exist_ok=True)
        output_path = os.path.join(OUTPUT_DIR, f'flyer_{registration.id}.png')

        # Check if output already exists (cache)
        if os.path.exists(output_path):
            return output_path

        # Validate and load base image
        if not os.path.exists(flyer_path):
            raise FileNotFoundError(f"Flyer base image not found at {flyer_path}")

        with Image.open(flyer_path) as base_img:
            base_img = base_img.convert("RGBA")
            draw = ImageDraw.Draw(base_img)
            img_width, img_height = base_img.size
            center_x = img_width // 2

            # Font loading with caching
            def load_font(path, size):
                try:
                    return ImageFont.truetype(path, size)
                except IOError:
                    try:
                        # Try system fonts as fallback
                        return ImageFont.truetype("arial.ttf", size) if "bd" not in path.lower() else ImageFont.truetype("arialbd.ttf", size)
                    except IOError:
                        # Final fallback to default font
                        default_font = ImageFont.load_default()
                        if "bd" in path.lower():
                            return default_font.font_variant(size=size, weight='bold')
                        return default_font.font_variant(size=size)

            # Preload fonts with optimized sizes
            name_font = load_font("arialbd.ttf", 60)
            role_font = load_font("arialbd.ttf", 48)
            
            current_y = 140  # Start position

            # Handle user image if exists
            if registration.image:
                try:
                    with default_storage.open(registration.image.name) as img_file:
                        with Image.open(img_file) as user_img:
                            user_img = user_img.convert("RGBA")
                            size = 400
                            
                            # Create circular mask
                            mask = Image.new('L', (size, size), 0)
                            draw_mask = ImageDraw.Draw(mask)
                            draw_mask.ellipse((0, 0, size, size), fill=255)
                            
                            # Resize and apply mask
                            user_img = user_img.resize((size, size), Image.LANCZOS)
                            circular_img = Image.new('RGBA', (size, size))
                            circular_img.paste(user_img, (0, 0), mask)
                            
                            # Position and paste
                            img_x = center_x - (size // 2)
                            base_img.paste(circular_img, (img_x, current_y), circular_img)
                            current_y += size + 40
                except Exception as e:
                    logger.warning(f"Error processing user image for registration {registration.id}: {str(e)}")

            # Draw name with stroke (optimized text positioning)
            name_text = registration.name.upper()
            name_bbox = draw.textbbox((0, 0), name_text, font=name_font)
            name_width = name_bbox[2] - name_bbox[0]
            name_position = (center_x - name_width // 2, current_y)
            draw.text(name_position, name_text, font=name_font, fill="white", 
                     stroke_width=3, stroke_fill="black")
            current_y += 75

            # Draw role with stroke
            role_text = registration.role.upper()
            role_bbox = draw.textbbox((0, 0), role_text, font=role_font)
            role_width = role_bbox[2] - role_bbox[0]
            role_position = (center_x - role_width // 2, current_y)
            draw.text(role_position, role_text, font=role_font, fill="yellow", 
                     stroke_width=3, stroke_fill="black")

            # Save optimized image
            base_img.save(output_path, quality=85, optimize=True)
            
            return output_path

    except Exception as e:
        logger.error(f"Error generating flyer for registration {registration.id}: {str(e)}")
        raise RuntimeError(f"Failed to generate flyer: {str(e)}")
    
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