from django.shortcuts import render, redirect
from django.http import HttpResponse
from django.core.paginator import Paginator
from django.conf import settings
from django.core.files.storage import default_storage
from django.contrib import messages
from django.urls import reverse
from django.templatetags.static import static

from .models import Attendee
from .forms import ConcertRegistrationForm

from PIL import Image, ImageDraw, ImageFont
from io import BytesIO
import os
import logging
import requests

logger = logging.getLogger(__name__)


# ----------------------------
# Concert Registration View
# ----------------------------
def concert_registration_view(request):
    if request.method == 'POST':
        form = ConcertRegistrationForm(request.POST, request.FILES)
        if form.is_valid():
            try:
                registration = form.save()
                flyer_path = generate_personalized_flyer(registration)
                
                # Save relative flyer path to model
                registration.generated_flyer.name = flyer_path.replace(str(settings.MEDIA_ROOT) + '/', '')
                registration.save()

                return redirect(reverse('flyer_preview', args=[registration.id]))

            except Exception as e:
                logger.error(f"Flyer generation error: {e}", exc_info=True)
                messages.error(request, 'There was an error generating your flyer. Please try again.')
                return render(request, 'index.html', {'form': form})
    else:
        form = ConcertRegistrationForm()

    return render(request, 'index.html', {'form': form})


# ----------------------------
# Load Web Font with Fallbacks
# ----------------------------
def load_web_font(font_url, size):
    """Load font from a URL with fallback to alternative URLs or system font"""
    try:
        response = requests.get(font_url, timeout=5)
        response.raise_for_status()
        return ImageFont.truetype(BytesIO(response.content), size)
    except requests.exceptions.RequestException:
        logger.warning(f"Primary font failed. Trying alternatives...")
        alternative_urls = [
            "https://raw.githubusercontent.com/google/fonts/main/apache/roboto/Roboto-Bold.ttf",
            "https://fonts.cdnfonts.com/s/14882/Roboto-Bold.ttf",
            "https://www.1001fonts.com/download/roboto-bold.ttf"
        ]
        for url in alternative_urls:
            try:
                response = requests.get(url, timeout=5)
                response.raise_for_status()
                return ImageFont.truetype(BytesIO(response.content), size)
            except requests.exceptions.RequestException:
                continue
        logger.warning("All font sources failed. Falling back to system default.")
        return ImageFont.load_default()


# ----------------------------
# Generate Personalized Flyer
# ----------------------------
def generate_personalized_flyer(registration):
    try:
        # Constants
        FLYER_FILENAME = 'flyer.png'
        OUTPUT_DIR = os.path.join(settings.MEDIA_ROOT, 'generated_flyers')
        os.makedirs(OUTPUT_DIR, exist_ok=True)

        flyer_path = os.path.join(settings.BASE_DIR, 'static', FLYER_FILENAME)
        if not os.path.exists(flyer_path):
            flyer_path = os.path.join(settings.MEDIA_ROOT, FLYER_FILENAME)

        if not os.path.exists(flyer_path):
            raise FileNotFoundError(f"Flyer image not found at {flyer_path}")

        output_path = os.path.join(OUTPUT_DIR, f'flyer_{registration.id}.png')
        if os.path.exists(output_path):
            return output_path

        with Image.open(flyer_path).convert("RGBA") as base_img:
            draw = ImageDraw.Draw(base_img)
            img_width, _ = base_img.size
            center_x = img_width // 2
            current_y = 140

            # Fonts
            name_font = load_web_font(
                "https://raw.githubusercontent.com/google/fonts/main/apache/roboto/Roboto-Bold.ttf", 60
            )
            role_font = load_web_font(
                "https://raw.githubusercontent.com/google/fonts/main/apache/roboto/Roboto-Bold.ttf", 48
            )

            # Add user image (circular)
            if registration.image:
                try:
                    image_path = getattr(registration.image, 'path', None)
                    if image_path and os.path.exists(image_path):
                        user_img = Image.open(image_path)
                    else:
                        with default_storage.open(registration.image.name) as f:
                            user_img = Image.open(f)

                    user_img = user_img.convert("RGBA")
                    size = 300
                    mask = Image.new('L', (size, size), 0)
                    ImageDraw.Draw(mask).ellipse((0, 0, size, size), fill=255)

                    user_img = user_img.resize((size, size), Image.LANCZOS)
                    circular_img = Image.new('RGBA', (size, size))
                    circular_img.paste(user_img, (0, 0), mask)

                    img_x = center_x - size // 2
                    base_img.paste(circular_img, (img_x, current_y), circular_img)
                    current_y += size + 40
                except Exception as e:
                    logger.warning(f"User image error: {e}")

            # Draw Name
            name_text = registration.name.upper()
            name_width = draw.textbbox((0, 0), name_text, font=name_font)[2]
            draw.text(
                (center_x - name_width // 2, current_y),
                name_text,
                font=name_font,
                fill="white",
                stroke_width=3,
                stroke_fill="black"
            )
            current_y += 75

            # Draw Role
            role_text = registration.role.upper()
            role_width = draw.textbbox((0, 0), role_text, font=role_font)[2]
            draw.text(
                (center_x - role_width // 2, current_y),
                role_text,
                font=role_font,
                fill="yellow",
                stroke_width=3,
                stroke_fill="black"
            )

            # Save flyer
            base_img.save(output_path, format='PNG', quality=85, optimize=True)
            os.chmod(output_path, 0o644)
            return output_path

    except Exception as e:
        logger.error(f"Flyer generation failed: {e}", exc_info=True)
        raise RuntimeError(f"Flyer generation failed: {e}")


# ----------------------------
# Flyer Preview View
# ----------------------------
def flyer_preview_view(request, pk):
    try:
        attendee = Attendee.objects.get(pk=pk)
        response = render(request, 'flyer_preview.html', {'attendee': attendee})
        response['Cache-Control'] = 'public, max-age=300'
        return response
    except Attendee.DoesNotExist:
        messages.error(request, "Flyer not found.")
        return redirect('index')


# ----------------------------
# Attendee List View
# ----------------------------
def attendee_list(request):
    attendees_list = Attendee.objects.all().order_by('-created_at')
    paginator = Paginator(attendees_list, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    return render(request, 'list.html', {
        'attendees': page_obj,
        'page_obj': page_obj,
        'is_paginated': paginator.num_pages > 1
    })
