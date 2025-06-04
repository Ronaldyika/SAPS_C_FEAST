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

def concert_registration_view(request):
    if request.method == 'POST':
        form = ConcertRegistrationForm(request.POST, request.FILES)
        if form.is_valid():
            try:
                # Save the form data to database
                registration = form.save()
                
                # Generate personalized flyer
                flyer_path = generate_personalized_flyer(registration)
                
                # Update the model with flyer path
                registration.generated_flyer.name = flyer_path.replace(settings.MEDIA_ROOT + '/', '')
                registration.save()
                
                # Serve the generated flyer for download
                with default_storage.open(registration.generated_flyer.name, 'rb') as f:
                    response = HttpResponse(f.read(), content_type='image/png')
                    response['Content-Disposition'] = f'attachment; filename="I_Will_Be_There_{registration.name}.png"'

                    return response
                    
            except Exception as e:
                print(f"Error generating flyer: {e}")
                messages.error(request, 'There was an error generating your flyer. Please try again.')
                return render(request, 'index.html', {'form': form})
    else:
        form = ConcertRegistrationForm()
    
    return render(request, 'index.html', {'form': form})

def generate_personalized_flyer(registration):
    # Get the correct path to the base flyer image
    static_image_path = os.path.join('image', 'flyer.png')
    base_flyer_path = os.path.join(settings.BASE_DIR, 'static', static_image_path)
    
    # Fallback to STATIC_ROOT if exists
    if hasattr(settings, 'STATIC_ROOT') and settings.STATIC_ROOT:
        base_flyer_path = os.path.join(settings.STATIC_ROOT, static_image_path)
    
    # Verify the file exists
    if not os.path.exists(base_flyer_path):
        raise FileNotFoundError(f"Base flyer image not found at {base_flyer_path}")
    
    base_img = Image.open(base_flyer_path).convert('RGBA')
    draw = ImageDraw.Draw(base_img)
    
    # Get image dimensions for positioning
    img_width, img_height = base_img.size
    
    # Calculate center positions
    center_x = img_width // 2
    content_start_y = img_height // 5 # Start content in upper middle
    
    # Font handling with appropriate sizes
    try:
        name_font = ImageFont.truetype("arialbd.ttf", 42)  # Larger for name
        role_font = ImageFont.truetype("arial.ttf", 32)    # Slightly smaller for role
    except:
        name_font = ImageFont.load_default()
        role_font = ImageFont.load_default()
    
    # Add user's image if provided
    if registration.image:
        try:
            with default_storage.open(registration.image.name) as img_file:
                user_img = Image.open(img_file).convert("RGBA")
                
                # Resize to appropriate dimensions (square aspect ratio)
                size = 250  # Increased size for better visibility
                user_img = user_img.resize((size, size))
                
                # Create circular mask
                mask = Image.new('L', (size, size), 0)
                draw_mask = ImageDraw.Draw(mask)
                draw_mask.ellipse((0, 0, size, size), fill=255)
                
                # Apply mask to create circular image
                circular_img = Image.new('RGBA', (size, size))
                circular_img.paste(user_img, (0, 0), mask)
                
                # Calculate position to center the image horizontally
                img_x = center_x - (size // 2)
                img_y = content_start_y
                
                # Paste circular user image onto flyer
                base_img.paste(circular_img, (img_x, img_y), circular_img)
                
                # Adjust text position below the image
                text_start_y = img_y + size + 20
        except Exception as e:
            print(f"Error processing user image: {e}")
            # Default text position if image fails
            text_start_y = content_start_y + 100
    else:
        # Default text position if no image
        text_start_y = content_start_y + 100
    
    # Calculate text widths for centering
    name_width = draw.textlength(registration.name, font=name_font)
    role_width = draw.textlength(registration.role, font=role_font)
    
    # Add name and role text (centered)
    draw.text(
        (center_x - (name_width // 2), text_start_y),
        registration.name, 
        fill="white", 
        font=name_font
    )
    
    draw.text(
        (center_x - (role_width // 2), text_start_y + 50),
        registration.role, 
        fill="white", 
        font=role_font
    )
    
    # Save the generated flyer
    output_dir = os.path.join(settings.MEDIA_ROOT, 'generated_flyers')
    os.makedirs(output_dir, exist_ok=True)
    output_path = os.path.join(output_dir, f'flyer_{registration.id}.png')
    
    base_img.save(output_path)
    
    return output_path