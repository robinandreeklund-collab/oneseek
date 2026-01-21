"use client";

import * as React from "react";
import * as AccordionPrimitive from "@radix-ui/react-accordion";
import { ChevronDown } from "lucide-react";
import { cn } from "@/lib/utils";

interface RetrievedDoc {
  title: string;
  content: string;
  relevance?: number;
}

interface TransparensAccordionProps {
  retrieved: RetrievedDoc[];
  steps: string[];
}

export function TransparensAccordion({ retrieved, steps }: TransparensAccordionProps) {
  if (!retrieved.length && !steps.length) {
    return null;
  }

  return (
    <AccordionPrimitive.Root
      type="single"
      collapsible
      className="w-full mt-4 border rounded-lg"
    >
      <AccordionPrimitive.Item value="sources">
        <AccordionPrimitive.Trigger className="flex w-full items-center justify-between px-4 py-3 text-sm font-medium transition-all hover:bg-accent [&[data-state=open]>svg]:rotate-180">
          <span>Källor & Steg ({retrieved.length} källor, {steps.length} steg)</span>
          <ChevronDown className="h-4 w-4 shrink-0 transition-transform duration-200" />
        </AccordionPrimitive.Trigger>
        <AccordionPrimitive.Content className="overflow-hidden text-sm transition-all data-[state=closed]:animate-accordion-up data-[state=open]:animate-accordion-down">
          <div className="px-4 pb-4 pt-0 space-y-4">
            {/* Processing Steps */}
            {steps.length > 0 && (
              <div>
                <h4 className="font-semibold mb-2 text-xs uppercase text-muted-foreground">
                  Processteg
                </h4>
                <ol className="space-y-1 list-decimal list-inside text-xs text-muted-foreground">
                  {steps.map((step, index) => (
                    <li key={index}>{step}</li>
                  ))}
                </ol>
              </div>
            )}

            {/* Retrieved Sources */}
            {retrieved.length > 0 && (
              <div>
                <h4 className="font-semibold mb-2 text-xs uppercase text-muted-foreground">
                  Hämtade Källor från Vespa
                </h4>
                <div className="space-y-3">
                  {retrieved.map((doc, index) => (
                    <div
                      key={index}
                      className="border rounded-md p-3 bg-muted/30"
                    >
                      <div className="flex items-start justify-between mb-1">
                        <h5 className="font-medium text-sm">{doc.title}</h5>
                        {doc.relevance !== undefined && (
                          <span className="text-xs text-muted-foreground ml-2">
                            Relevans: {doc.relevance.toFixed(3)}
                          </span>
                        )}
                      </div>
                      <p className="text-xs text-muted-foreground line-clamp-3">
                        {doc.content}
                      </p>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        </AccordionPrimitive.Content>
      </AccordionPrimitive.Item>
    </AccordionPrimitive.Root>
  );
}
