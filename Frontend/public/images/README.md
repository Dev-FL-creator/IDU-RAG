# Images Folder Structure

This folder contains all static images and figures for the website.

## Folder Organization

```
public/images/
├── avatars/           # User avatars, profile pictures
├── charts/            # Charts, graphs, data visualizations
├── figures/           # Figures, diagrams, analysis images
├── icons/             # Icons, logos, small graphics
├── backgrounds/       # Background images, patterns
└── README.md          # This file
```

## How to Use Images

### 1. Place Your Images
Put your images in the appropriate subfolder:
- User photos → `public/images/avatars/`
- Charts/graphs → `public/images/charts/`
- Figures/diagrams → `public/images/figures/`
- Icons/logos → `public/images/icons/`
- Backgrounds → `public/images/backgrounds/`

### 2. Reference in Code

#### Using Next.js Image Component (Recommended)
```tsx
import Image from "next/image"

// Example: Using an avatar
<Image
  src="/images/avatars/user1.jpg"
  alt="User avatar"
  width={200}
  height={200}
/>

// Example: Using a chart
<Image
  src="/images/charts/sales-2024.png"
  alt="Sales chart 2024"
  width={600}
  height={400}
/>
```

#### Using Regular img Tag
```tsx
<img src="/images/icons/logo.png" alt="Logo" />
```

### 3. In Message Component
```tsx
const message: Message = {
  id: "1",
  role: "assistant",
  contents: [
    {
      type: "text",
      content: "Here's the chart you requested:",
    },
    {
      type: "image",
      content: "/images/charts/sales-chart.png",
      alt: "Sales performance chart",
    },
  ],
}
```

## Supported Formats
- **Images**: .jpg, .jpeg, .png, .gif, .webp, .svg
- **Recommended**: Use .webp for better compression
- **Icons**: .svg for scalability

## Best Practices
1. Use descriptive filenames (e.g., `sales-chart-q4-2024.png`)
2. Keep file sizes small (compress before uploading)
3. Use appropriate dimensions (don't upload 4K images if you only need 800px)
4. Add alt text for accessibility
