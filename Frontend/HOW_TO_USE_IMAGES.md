# How to Use Images in Your Application

## 📁 Folder Structure

Your images should be placed in the `public/images/` folder:

```
public/
└── images/
    ├── avatars/        # Profile pictures, user avatars
    ├── charts/         # Charts, graphs, visualizations
    ├── icons/          # Icons, logos, badges
    └── backgrounds/    # Background images, patterns
```

## 🖼️ Adding Your Images

### Step 1: Copy Images to the Folder
Place your images in the appropriate subfolder:

```bash
# Example: Copy a chart image
cp ~/Downloads/my-chart.png public/images/charts/

# Example: Copy an avatar
cp ~/Downloads/profile.jpg public/images/avatars/
```

### Step 2: Reference in Your Code

#### Method A: In Message Component (for chat)
```typescript
const message: Message = {
  id: "1",
  role: "assistant",
  contents: [
    {
      type: "text",
      content: "Here's the analysis:",
    },
    {
      type: "image",
      content: "/images/charts/my-chart.png",  // ← Your image path
      alt: "Sales analysis chart",
    },
  ],
}
```

#### Method B: Using Next.js Image Component
```tsx
import Image from "next/image"

<Image
  src="/images/avatars/profile.jpg"  // ← Your image path
  alt="Profile picture"
  width={200}
  height={200}
/>
```

#### Method C: Using Regular HTML img Tag
```tsx
<img 
  src="/images/icons/logo.svg"  // ← Your image path
  alt="Logo" 
/>
```

## 🎯 Real Examples

### Example 1: Show a Chart in Conversation
```typescript
// In your app/page.tsx or any component
const handleSendChart = () => {
  const chartMessage: Message = {
    id: Date.now().toString(),
    role: "assistant",
    contents: [
      {
        type: "text",
        content: "Here's your Q1 2024 sales performance:",
      },
      {
        type: "image",
        content: "/images/charts/q1-sales.png",
        alt: "Q1 2024 Sales Chart",
      },
      {
        type: "text",
        content: "Revenue increased by 35% compared to Q4 2023.",
      },
    ],
  }
  
  setMessages(prev => [...prev, chartMessage])
}
```

### Example 2: Multiple Images in One Message
```typescript
const multiImageMessage: Message = {
  id: "1",
  role: "assistant",
  contents: [
    { type: "text", content: "Here are the comparison charts:" },
    { type: "image", content: "/images/charts/chart1.png", alt: "Chart 1" },
    { type: "image", content: "/images/charts/chart2.png", alt: "Chart 2" },
    { type: "text", content: "Both show positive growth trends." },
  ],
}
```

### Example 3: Using the Helper Function
```typescript
import { getImagePath } from "@/lib/image-examples"

const message: Message = {
  id: "1",
  role: "assistant",
  contents: [
    {
      type: "image",
      content: getImagePath("charts", "sales-2024.png"),
      alt: "Sales Chart",
    },
  ],
}
```

## 📝 Path Rules

**Important:** All paths start with `/images/` (note the leading slash)

✅ Correct:
- `/images/charts/sales.png`
- `/images/avatars/user1.jpg`
- `/images/icons/logo.svg`

❌ Incorrect:
- `images/charts/sales.png` (missing leading slash)
- `public/images/charts/sales.png` (don't include "public")
- `./images/charts/sales.png` (use absolute path)

## 🎨 Supported Formats

- **Photos**: .jpg, .jpeg, .png, .webp
- **Graphics**: .svg, .png
- **Animations**: .gif, .webp

## 💡 Tips

1. **Use descriptive names**: `sales-chart-q1-2024.png` instead of `chart1.png`
2. **Keep organized**: Use the subfolders to categorize images
3. **Optimize size**: Compress images before uploading
4. **Add alt text**: Always provide descriptive alt text for accessibility

## 🚀 Quick Start

1. Add your image:
   ```bash
   cp ~/Downloads/my-image.png public/images/charts/
   ```

2. Use in your app:
   ```typescript
   {
     type: "image",
     content: "/images/charts/my-image.png",
     alt: "Description of image",
   }
   ```

That's it! Your image will now display in the chat interface.
