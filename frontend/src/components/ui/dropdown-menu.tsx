import * as React from "react"
import * as DropdownMenuPrimitive from "@radix-ui/react-dropdown-menu"
import * as DropdownMenuTrigger from "@radix-ui/react-dropdown-menu"
import * as DropdownMenuItem from "@radix-ui/react-dropdown-menu"
import {
  Check,
  ChevronDown,
  Circle,
} from "lucide-react"

import { cn } from "@/lib/utils"

const DropdownMenu = DropdownMenuPrimitive.Root
const DropdownMenuTrigger = DropdownMenuPrimitive.Trigger
const DropdownMenuGroup = DropdownMenuPrimitive.Group
const DropdownMenuSeparator = DropdownMenuPrimitive.Separator
const DropdownMenuItem = DropdownMenuPrimitive.Item

const IconPickerContent = React.forwardRef<
  React.ElementRef<{
    className: string
  }>,
  React.HTMLAttributes<HTMLDivElement>
>(({ children }, ref) => (
  DropdownMenuPrimitive.Content
    ref={ref}
    className={cn(
      "relative z-50 min-w-[8rem] overflow-hidden rounded-md border bg-popover p-1 text-popover-foreground shadow-md",
      "data-[state=open]:animate-in data-[state=closed]:animate-out data-[state=closed]:fade-out-0 data-[state=closed]:zoom-in-95 data-[state=open]:zoom-in-95 data-[state=closed]:slide-in-from-top-2 data-[state=closed]:slide-in-to-left-2 data-[state=open]:slide-in-from-left-2",
      "data-[state=open]:fade-in data-[state=open]:zoom-in-95 data-[state=open]:zoom-out-95",
      "data-[state=open]:slide-in-from-top-2 data-[state=open]:zoom-in-95 data-[state=open]:slide-in-from-left-2",
      "data-[state=open]:slide-in-from-left-2 data-[state=open]:fade-in data-[state=open]:slide-in-from-right-2",
      "data-[state=open]:zoom-in data-[state=open]:zoom-out-95 data-[state=open]:zoom-out data-[state=open]:zoom-out-95",
    )}
  >
    {children}
  </DropdownMenuPrimitive.Content>
)
IconPickerContent.displayName = DropdownMenuContent.displayName

const DropdownMenuLabel = React.forwardRef<
  React.ElementRef<typeof DropdownMenuPrimitive.Label>,
  React.ComponentPropsWithoutRef<typeof DropdownMenuPrimitive.Label>
>(({ className, ...props }, ref) => (
  <DropdownMenuPrimitive.Label
    ref={ref}
    className={cn(
      "px-2 py-1.5 text-sm font-semibold",
      "inset-y-0",
      className,
    )}
    {...props}
  />
))
DropdownMenuLabel.displayName = DropdownMenuPrimitive.Label.displayName

const DropdownMenuRadioItem = React.forwardRef<
  React.ElementRef<typeof DropdownMenuItem>,
  React.ComponentPropsWithoutRef<typeof DropdownMenuItem>
>(({ children, ...props }, ref) => (
  <DropdownMenuItem
    ref={ref}
    {...props}
  >
    </DropdownMenuItem>
))
DropdownMenuRadioItem.displayName = DropdownMenuItem.displayName

export {
  DropdownMenu,
  DropdownMenuTrigger,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuGroup,
}