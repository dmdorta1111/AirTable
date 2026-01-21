import * as React from "react"

interface PopoverProps extends React.HTMLAttributes<HTMLDivElement> {
  [key: string]: any
}

const Popover = React.forwardRef<HTMLDivElement, PopoverProps>(
  ({ children, ...props }, ref) => (
    <div ref={ref} {...props}>
      {children}
    </div>
  )
)
Popover.displayName = "Popover"

const PopoverTrigger = React.forwardRef<HTMLDivElement, PopoverProps>(
  ({ children, asChild, ...props }, ref) => (
    <div ref={ref} {...props}>
      {children}
    </div>
  )
)
PopoverTrigger.displayName = "PopoverTrigger"

const PopoverContent = React.forwardRef<HTMLDivElement, PopoverProps>(
  ({ children, className = "", align, ...props }, ref) => (
    <div
      ref={ref}
      className={`z-50 rounded-md border bg-popover p-4 text-popover-foreground shadow-md ${className}`}
      {...props}
    >
      {children}
    </div>
  )
)
PopoverContent.displayName = "PopoverContent"

export { Popover, PopoverTrigger, PopoverContent }
