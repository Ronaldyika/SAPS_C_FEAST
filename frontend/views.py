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
import os
from PIL import Image, ImageDraw, ImageFont
from django.conf import settings
from django.core.files.storage import default_storage
import logging
import sys

logger = logging.getLogger(__name__)

def generate_personalized_flyer(registration):
    try:
        # Predefined constants - use absolute paths
        FLYER_FILENAME = 'flyer.png'
        OUTPUT_DIR = os.path.join(settings.MEDIA_ROOT, 'generated_flyers')
        
        # Ensure directories exist
        os.makedirs(OUTPUT_DIR, exist_ok=True)
        os.makedirs(settings.MEDIA_ROOT, exist_ok=True)

        # Path handling for cloud compatibility
        flyer_path = os.path.join(settings.BASE_DIR, 'static', FLYER_FILENAME)
        if not os.path.exists(flyer_path):
            flyer_path = os.path.join(settings.MEDIA_ROOT, FLYER_FILENAME)
        
        output_path = os.path.join(OUTPUT_DIR, f'flyer_{registration.id}.png')

        # Check cache
        if os.path.exists(output_path):
            return output_path

        # Verify base image exists
        if not os.path.exists(flyer_path):
            raise FileNotFoundError(f"Flyer base image not found at {flyer_path}")

        # Font path configuration for cloud
        def get_font_path(font_name):
            # Try system fonts first
            system_fonts = [
                f"/usr/share/fonts/truetype/{font_name}",
                f"/usr/share/fonts/{font_name}",
                f"/Library/Fonts/{font_name}",  # macOS
                f"C:/Windows/Fonts/{font_name}"  # Windows
            ]
            
            for path in system_fonts:
                if os.path.exists(path):
                    return path
            
            # Fallback to bundled fonts (should be in your static files)
            static_font = os.path.join(settings.BASE_DIR, 'static', 'fonts', font_name)
            if os.path.exists(static_font):
                return static_font
            
            return font_name  # Final fallback to hope system finds it

        with Image.open(flyer_path) as base_img:
            base_img = base_img.convert("RGBA")
            draw = ImageDraw.Draw(base_img)
            img_width, img_height = base_img.size
            center_x = img_width // 2

            # Improved font loading with better error handling
            def load_font(font_name, size):
                font_path = get_font_path(font_name)
                try:
                    return ImageFont.truetype(font_path, size)
                except IOError as e:
                    logger.warning(f"Failed to load font {font_name} from {font_path}: {str(e)}")
                    try:
                        # Try default system fonts
                        return ImageFont.truetype("arial.ttf", size) if "bd" not in font_name.lower() else ImageFont.truetype("arialbd.ttf", size)
                    except IOError:
                        # Final fallback
                        default_font = ImageFont.load_default()
                        if "bd" in font_name.lower():
                            return default_font.font_variant(size=size, weight='bold')
                        return default_font.font_variant(size=size)

            # Font loading with explicit paths
            name_font = load_font("arialbd.ttf", 60)
            role_font = load_font("arialbd.ttf", 48)
            
            current_y = 140

            # Handle user image with better cloud storage handling
            if registration.image:
                try:
                    # Use default_storage properly for cloud
                    if hasattr(registration.image, 'path'):
                        img_path = registration.image.path
                        if os.path.exists(img_path):
                            user_img = Image.open(img_path)
                        else:
                            with default_storage.open(registration.image.name) as img_file:
                                user_img = Image.open(img_file)
                    else:
                        with default_storage.open(registration.image.name) as img_file:
                            user_img = Image.open(img_file)

                    user_img = user_img.convert("RGBA")
                    size = 300
                    
                    # Circular mask
                    mask = Image.new('L', (size, size), 0)
                    draw_mask = ImageDraw.Draw(mask)
                    draw_mask.ellipse((0, 0, size, size), fill=255)
                    
                    user_img = user_img.resize((size, size), Image.LANCZOS)
                    circular_img = Image.new('RGBA', (size, size))
                    circular_img.paste(user_img, (0, 0), mask)
                    
                    img_x = center_x - (size // 2)
                    base_img.paste(circular_img, (img_x, current_y), circular_img)
                    current_y += size + 40
                except Exception as e:
                    logger.error(f"Image processing error for {registration.id}: {str(e)}")
                    # Continue without image rather than failing

            # Text rendering
            name_text = registration.name.upper()
            name_bbox = draw.textbbox((0, 0), name_text, font=name_font)
            name_width = name_bbox[2] - name_bbox[0]
            draw.text(
                (center_x - name_width // 2, current_y),
                name_text,
                font=name_font,
                fill="white",
                stroke_width=3,
                stroke_fill="black"
            )
            current_y += 75

            role_text = registration.role.upper()
            role_bbox = draw.textbbox((0, 0), role_text, font=role_font)
            role_width = role_bbox[2] - role_bbox[0]
            draw.text(
                (center_x - role_width // 2, current_y),
                role_text,
                font=role_font,
                fill="yellow",
                stroke_width=3,
                stroke_fill="black"
            )

            # Save with proper permissions
            base_img.save(output_path, quality=85, optimize=True)
            os.chmod(output_path, 0o644)  # Ensure readable permissions
            
            return output_path

    except Exception as e:
        logger.error(f"Critical flyer generation error: {str(e)}", exc_info=True)
        raise RuntimeError(f"Flyer generation failed: {str(e)}")

def flyer_preview_view(request, pk):
    try:
        attendee = Attendee.objects.get(pk=pk)
        # Add cache headers for better performance
        response = render(request, 'flyer_preview.html', {'attendee': attendee})
        response['Cache-Control'] = 'public, max-age=300'
        return response
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
