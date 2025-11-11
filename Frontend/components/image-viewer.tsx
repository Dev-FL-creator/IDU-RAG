"use client"

import { useState } from "react"
import Image from "next/image"
import { Dialog, DialogContent, DialogTitle, DialogDescription } from "@/components/ui/dialog"
import { VisuallyHidden } from "@/components/ui/visually-hidden"
import { ZoomIn } from "lucide-react"

interface ImageViewerProps {
  src: string
  alt: string
  className?: string
}

export function ImageViewer({ src, alt, className }: ImageViewerProps) {
  const [isOpen, setIsOpen] = useState(false)

  return (
    <>
      {/* Thumbnail - Click to open */}
      <div
        className={`relative group cursor-pointer rounded-md overflow-hidden bg-muted ${className}`}
        onClick={() => setIsOpen(true)}
      >
        <Image
          src={src}
          alt={alt}
          width={400}
          height={300}
          className="w-full h-auto object-cover transition-transform group-hover:scale-105"
          unoptimized
        />
        {/* Overlay with zoom icon */}
        <div className="absolute inset-0 bg-black/0 group-hover:bg-black/40 transition-all flex items-center justify-center">
          <ZoomIn className="h-8 w-8 text-white opacity-0 group-hover:opacity-100 transition-opacity" />
        </div>
      </div>

      {/* Full-size Modal */}
      <Dialog open={isOpen} onOpenChange={setIsOpen}>
        <DialogContent className="max-w-[90vw] max-h-[90vh] p-0 overflow-hidden">
          <VisuallyHidden>
            <DialogTitle>{alt || "Image viewer"}</DialogTitle>
            <DialogDescription>
              Full-size image view. Press Escape or click the X button to close.
            </DialogDescription>
          </VisuallyHidden>
          <div className="relative w-full h-full flex items-center justify-center bg-black">
            <Image
              src={src}
              alt={alt}
              width={1200}
              height={900}
              className="max-w-full max-h-[90vh] w-auto h-auto object-contain"
              unoptimized
            />
          </div>
          {alt && (
            <div className="absolute bottom-0 left-0 right-0 bg-black/80 text-white p-4 text-sm">
              {alt}
            </div>
          )}
        </DialogContent>
      </Dialog>
    </>
  )
}
