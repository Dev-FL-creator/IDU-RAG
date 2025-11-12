# IDU - AI Assistant Interface

A modern, feature-rich chat interface built with Next.js, React, and shadcn/ui for LLM-powered conversations with support for images and interactive company data.

## Features

### 🎨 Beautiful UI
- Modern, responsive design with gradient effects
- Dark/light mode support through CSS variables
- Smooth animations and transitions
- Professional color palette

### 💬 Rich Messaging
- Text messages with markdown support
- Image support with click-to-enlarge lightbox
- Interactive company cards
- Multi-content messages (mix text, images, and companies)
- Avatar-based chat interface

### 🏢 Company Data Display
- Interactive company cards in conversations
- Detailed company view panel
- Company metrics with trend indicators
- Image galleries
- Circular company icons

### 📱 Responsive Layout
- Three-panel resizable layout
  - Collapsible sidebar (conversation history & projects)
  - Main chat area
  - Company detail panel (opens on demand)
- Drag-to-resize functionality
- Mobile-responsive design

### 🔧 Key Components
- **Sidebar**: Project list, conversation history, new conversation button
- **Chat Area**: Message display, text input, image sharing
- **Detail Panel**: Company information, metrics, image gallery
- **Image Viewer**: Click-to-enlarge modal for all images

## Tech Stack

- **Framework**: [Next.js 16](https://nextjs.org/) with App Router
- **Language**: TypeScript
- **UI Components**: [shadcn/ui](https://ui.shadcn.com/)
- **Styling**: [Tailwind CSS](https://tailwindcss.com/)
- **Icons**: [Lucide React](https://lucide.dev/)
- **Layout**: [react-resizable-panels](https://github.com/bvaughn/react-resizable-panels)
- **UI Primitives**: [Radix UI](https://www.radix-ui.com/)

## Getting Started

### Prerequisites

- Node.js 18+
- npm, yarn, or pnpm

### Installation

1. Clone the repository:
```bash
git clone <your-repo-url>
cd idu
```

2. Install dependencies:
```bash
npm install
```

3. Run the development server:
启动backend
```bash
 cd "C:\Users\jinkliu\Desktop\Jinkai Docs\IDU-RAG\Backend"; .\azure_openai_env\Scripts\Activate.ps1; python main.py
```
启动Frontend
```bash
 cd Frontend; $env:PATH += ";C:\Users\jinkliu\Desktop\Jinkai Docs\IDU-RAG\node-v24.8.0-win-x64"; npm.cmd run dev
 ```


4. Open [http://localhost:3000](http://localhost:3000) in your browser

### Build for Production

```bash
npm run build
npm run start
```

## Project Structure

```
idu/
├── app/                      # Next.js App Router
│   ├── layout.tsx           # Root layout
│   ├── page.tsx             # Main chat page
│   └── globals.css          # Global styles
├── components/              # React components
│   ├── ui/                  # shadcn/ui components
│   │   ├── button.tsx
│   │   ├── card.tsx
│   │   ├── dialog.tsx
│   │   ├── input.tsx
│   │   └── ...
│   ├── chat-input.tsx       # Message input component
│   ├── company-card.tsx     # Company card display
│   ├── company-detail-panel.tsx  # Company details
│   ├── image-viewer.tsx     # Image lightbox
│   ├── message.tsx          # Message component
│   └── sidebar.tsx          # Sidebar navigation
├── lib/                     # Utilities and helpers
│   ├── utils.ts             # Utility functions
│   ├── image-examples.ts    # Image path helpers
│   └── mock-companies.ts    # Sample company data
├── types/                   # TypeScript types
│   └── company.ts           # Company interfaces
├── public/                  # Static assets
│   └── images/              # Image storage
│       ├── avatars/         # Profile pictures
│       ├── charts/          # Charts and graphs
│       ├── figures/         # General figures
│       ├── icons/           # Icons and logos
│       └── backgrounds/     # Background images
├── tailwind.config.ts       # Tailwind configuration
├── tsconfig.json            # TypeScript configuration
├── next.config.mjs          # Next.js configuration
└── package.json             # Dependencies
```

## Usage

### Adding Images

Place images in the appropriate folder:
```
public/images/
├── avatars/        # User/company avatars
├── charts/         # Charts and graphs
├── figures/        # General images
├── icons/          # Icons and logos
└── backgrounds/    # Background images
```

Reference in code:
```tsx
// In a message
{
  type: "image",
  content: "/images/figures/my-image.jpg",
  alt: "Description"
}
```

See [HOW_TO_USE_IMAGES.md](./HOW_TO_USE_IMAGES.md) for detailed instructions.

### Adding Company Data

Create company objects:
```typescript
const company: Company = {
  id: "1",
  name: "Company Name",
  icon: "/images/avatars/logo.png",
  shortDescription: "Brief description",
  fullDescription: "Detailed description",
  industry: "Technology",
  founded: "2020",
  location: "San Francisco, CA",
  website: "https://example.com",
  images: [
    {
      url: "/images/figures/photo.jpg",
      alt: "Photo description",
      caption: "Optional caption"
    }
  ],
  metrics: [
    {
      label: "Revenue",
      value: "$10M",
      trend: "up"  // "up" | "down" | "neutral"
    }
  ]
}
```

Display in messages:
```typescript
{
  type: "company",
  content: company.name,
  company: company
}
```

### Message Types

The system supports three message types:

1. **Text Messages**:
```typescript
{
  type: "text",
  content: "Your message here"
}
```

2. **Image Messages**:
```typescript
{
  type: "image",
  content: "/images/figures/chart.png",
  alt: "Chart description"
}
```

3. **Company Messages**:
```typescript
{
  type: "company",
  content: "Company Name",
  company: companyObject
}
```

### Connecting to an API

Replace the mock data in `app/page.tsx`:

```typescript
const handleSendMessage = async (content: string) => {
  const userMessage: Message = {
    id: Date.now().toString(),
    role: "user",
    contents: [{ type: "text", content }],
  }
  setMessages((prev) => [...prev, userMessage])

  // Call your API
  const response = await fetch("/api/chat", {
    method: "POST",
    body: JSON.stringify({ message: content }),
  })

  const data = await response.json()

  setMessages((prev) => [...prev, data.message])
}
```

## Configuration

### Tailwind CSS

Customize colors and theme in `tailwind.config.ts` and `app/globals.css`.

### Next.js

Configure Next.js settings in `next.config.mjs`:
- Image domains
- Environment variables
- Build settings

### TypeScript

Adjust TypeScript settings in `tsconfig.json`.

## Available Scripts

- `npm run dev` - Start development server
- `npm run build` - Build for production
- `npm run start` - Start production server
- `npm run lint` - Run ESLint

## Features Breakdown

### Sidebar Features
- Project selection (Project 1, Project 2)
- Conversation history with previews
- New conversation button
- Collapsible/expandable
- Tooltips when collapsed

### Chat Features
- User and assistant messages
- Multi-part messages
- Image attachments with thumbnails
- Click-to-enlarge images
- Company cards
- Auto-scroll to latest message

### Company Detail Features
- Company header with logo
- Industry badge
- Location, founding date, website
- Full description
- Metrics grid with trends
- Image gallery
- Scrollable content
- Close button

### Panel Resizing
- Sidebar: 15%-35% width
- Chat: 30%+ width
- Detail: 25%-50% width
- Smooth transitions
- Persistent sizing during session

## Accessibility

- Screen reader support
- Keyboard navigation
- ARIA labels
- Semantic HTML
- Focus indicators
- Alt text for images

## Browser Support

- Chrome (latest)
- Firefox (latest)
- Safari (latest)
- Edge (latest)

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test thoroughly
5. Submit a pull request

## License

ISC

## Support

For issues and questions, please open an issue on GitHub.

## Acknowledgments

- [shadcn/ui](https://ui.shadcn.com/) for the beautiful components
- [Radix UI](https://www.radix-ui.com/) for accessible primitives
- [Lucide](https://lucide.dev/) for icons
- [Next.js](https://nextjs.org/) team for the amazing framework

---

Built with ❤️ using Next.js and React
