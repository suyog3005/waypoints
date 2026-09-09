import * as React from "react";
import { Slot } from "@radix-ui/react-slot";
import { cva, type VariantProps } from "class-variance-authority";

import { cn } from "@/lib/utils";

const separatorVariants = cva(
  "shrink-0 bg-border",
  {
    variants: {
      orientation: {
        horizontal: "h-[1px] w-full",
        vertical: "h-full w-[1px]",
      },
    },
    defaultVariants: {
      orientation: "horizontal",
    },
  },
);

const Separator = React.forwardRef<
  HTMLDivElement,
  React.HTMLAttributes<HTMLDivElement> &
    VariantProps<typeof separatorVariants> & {
      decorative?: boolean;
    }
>(
  (
    { className, orientation = "horizontal", decorative = true, ...props },
    ref,
  ) => (
    <div
      ref={ref}
      role={decorative ? "none" : "separator"}
      aria-orientation={decorative ? undefined : (orientation as "horizontal" | "vertical")}
      className={cn(
        separatorVariants({ orientation }),
        className,
      )}
      {...props}
    />
  ),
);
Separator.displayName = Slot.displayName;

export { Separator };
