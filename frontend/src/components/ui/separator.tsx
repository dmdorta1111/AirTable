import * as React from "react"

const Separator = React.forwardRef<
  HTMLHRElement,
  React.HTMLAttributes<HTMLHRElement>
>(({ className = "", ...props }, ref) => (
  <hr
    ref={ref}
    className={`border-t border-border ${className}`}
    {...props}
  />
))
Separator.displayName = "Separator"

export { Separator }
