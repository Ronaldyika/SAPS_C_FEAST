from django.shortcuts import render, redirect
from django.http import HttpResponse
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
        # Get the correct path to the base flyer image
        static_image_path = os.path.join('image', 'flyer.png')
        base_flyer_path = os.path.join(settings.BASE_DIR, 'static', static_image_path)
        
        # Fallback to STATIC_ROOT if exists
        if hasattr(settings, 'STATIC_ROOT') and settings.STATIC_ROOT:
            base_flyer_path = os.path.join(settings.STATIC_ROOT, static_image_path)
        
        # Verify the file exists
        if not os.path.exists(base_flyer_path):
            raise FileNotFoundError(f"Base flyer image not found at {base_flyer_path}")
        
        # Open base image with error handling
        try:
            base_img = Image.open(base_flyer_path).convert('RGBA')
        except Exception as e:
            raise ValueError(f"Failed to open base image: {str(e)}")
        
        draw = ImageDraw.Draw(base_img)
        
        # Get image dimensions for positioning
        img_width, img_height = base_img.size
        
        # Calculate center positions
        center_x = img_width // 2
        
        # Font handling with fallbacks and appropriate sizes
        try:
            # Professional font choices with different weights
            title_font = ImageFont.truetype("arialbd.ttf", 48) if os.path.exists("arialbd.ttf") else ImageFont.load_default(48)
            name_font = ImageFont.truetype("arialbd.ttf", 42) if os.path.exists("arialbd.ttf") else ImageFont.load_default(42)
            role_font = ImageFont.truetype("arial.ttf", 32) if os.path.exists("arial.ttf") else ImageFont.load_default(32)
            details_font = ImageFont.truetype("arial.ttf", 24) if os.path.exists("arial.ttf") else ImageFont.load_default(24)
        except Exception as e:
            print(f"Font loading error: {e}")
            # Default fonts with appropriate sizes
            title_font = ImageFont.load_default(48)
            name_font = ImageFont.load_default(42)
            role_font = ImageFont.load_default(32)
            details_font = ImageFont.load_default(24)
        
        # Calculate vertical positions for all elements
        current_y = img_height // 12  # Start position
    
        
        # Add user's image if provided
        if registration.image:
            try:
                with default_storage.open(registration.image.name) as img_file:
                    user_img = Image.open(img_file).convert("RGBA")
                    
                    # Resize to appropriate dimensions (square aspect ratio)
                    size = min(400, img_width // 2)  # Responsive size
                    user_img = user_img.resize((size, size))
                    
                    # Create circular mask with border
                    mask = Image.new('L', (size, size), 0)
                    draw_mask = ImageDraw.Draw(mask)
                    draw_mask.ellipse((0, 0, size, size), fill=255)
                    
                    # Create border for the circle
                    border = Image.new('RGBA', (size + 10, size + 10), (0, 0, 0, 0))
                    draw_border = ImageDraw.Draw(border)
                    draw_border.ellipse((0, 0, size + 10, size + 10), outline="white", width=5)
                    
                    # Apply mask to create circular image
                    circular_img = Image.new('RGBA', (size, size))
                    circular_img.paste(user_img, (0, 0), mask)
                    
                    # Combine image with border
                    final_img = Image.new('RGBA', (size + 10, size + 10), (0, 0, 0, 0))
                    final_img.paste(border, (0, 0))
                    final_img.paste(circular_img, (5, 5), circular_img)
                    
                    # Calculate position to center the image horizontally
                    img_x = center_x - (final_img.width // 2)
                    
                    # Paste circular user image onto flyer
                    base_img.paste(final_img, (img_x, current_y), final_img)
                    
                    # Adjust text position below the image
                    current_y += final_img.height + 30
                    
            except Exception as e:
                print(f"Error processing user image: {e}")
                # Default text position if image fails
                current_y += 100
        else:
            # Default text position if no image
            current_y += 100
        
        # Add name with shadow effect
        name = registration.name.upper()  # All caps for professional look
        name_width = draw.textlength(name, font=name_font)
        
        # Shadow effect
        draw.text(
            (center_x - (name_width // 2) + 2, current_y + 2),
            name,
            fill="black",
            font=name_font
        )
        # Main text
        draw.text(
            (center_x - (name_width // 2), current_y),
            name,
            fill="white",
            font=name_font
        )
        current_y += 60  # Increased spacing
        
        # Add role with smaller font
        role = registration.role.upper()
        role_width = draw.textlength(role, font=role_font)
        
        # Shadow effect
        draw.text(
            (center_x - (role_width // 2) + 2, current_y + 2),
            role,
            fill="black",
            font=role_font
        )
        # Main text
        draw.text(
            (center_x - (role_width // 2), current_y),
            role,
            fill="#f0f0f0",  # Slightly off-white
            font=role_font
        )
        current_y += 50
        
        # Add event details at the bottom
        details = "Our Lady of Fatima Parish Hall Bambili"
        details_width = draw.textlength(details, font=details_font)
        draw.text(
            (center_x - (details_width // 2), img_height - 80),
            details,
            fill="white",
            font=details_font
        )
        
        # Add decorative elements (optional)
        # Horizontal lines above and below name
        line_length = min(name_width + 100, img_width - 100)
        draw.line(
            [(center_x - line_length//2, current_y - 30), 
             (center_x + line_length//2, current_y - 30)],
            fill="white",
            width=2
        )
        draw.line(
            [(center_x - line_length//2, current_y - 10), 
             (center_x + line_length//2, current_y - 10)],
            fill="white",
            width=2
        )
        
        # Save the generated flyer with quality settings
        output_dir = os.path.join(settings.MEDIA_ROOT, 'generated_flyers')
        os.makedirs(output_dir, exist_ok=True)
        output_path = os.path.join(output_dir, f'flyer_{registration.id}.png')
        
        # Save with high quality
        base_img.save(output_path, quality=95, dpi=(300, 300))
        
        return output_path
    
    except Exception as e:
        print(f"Error generating flyer: {e}")
        raise  # Re-raise the exception for handling upstream


def flyer_preview_view(request, pk):
    try:
        attendee = Attendee.objects.get(pk=pk)
        return render(request, 'flyer_preview.html', {'attendee': attendee})
    except Attendee.DoesNotExist:
        messages.error(request, "Flyer not found.")
        return redirect('index')
