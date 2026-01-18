import React from 'react';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';

interface FormViewProps {
  fields: any[];
  onSubmit?: (data: any) => void;
}

export const FormView: React.FC<FormViewProps> = ({ fields, onSubmit }) => {
  return (
    <div className="max-w-2xl mx-auto py-8 px-4">
        <div className="bg-primary h-32 rounded-t-lg mb-[-40px]"></div>
        <Card className="shadow-lg relative z-10">
            <CardHeader className="text-center pt-8">
                <CardTitle className="text-3xl">Submit a Record</CardTitle>
                <CardDescription>Fill out the form below to add a new record to the table.</CardDescription>
            </CardHeader>
            <CardContent className="space-y-6 pt-6">
                {fields.map(field => (
                    <div key={field.id} className="space-y-2">
                        <Label htmlFor={field.id} className="text-base">
                            {field.name}
                            {field.required && <span className="text-red-500 ml-1">*</span>}
                        </Label>
                        {field.description && (
                            <p className="text-xs text-muted-foreground">{field.description}</p>
                        )}
                        
                        {/* Simplified input rendering based on type */}
                        {field.type === 'longText' ? (
                            <textarea 
                                className="flex min-h-[80px] w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50"
                                placeholder={`Enter ${field.name}...`}
                            />
                        ) : field.type === 'select' ? (
                            <select className="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50">
                                <option value="">Select an option...</option>
                                {field.options?.choices?.map((c: any) => (
                                    <option key={c.name || c} value={c.name || c}>{c.name || c}</option>
                                ))}
                            </select>
                        ) : (
                            <Input 
                                id={field.id} 
                                type={field.type === 'number' ? 'number' : field.type === 'date' ? 'date' : 'text'} 
                                placeholder={`Your answer`}
                            />
                        )}
                    </div>
                ))}
                
                <div className="pt-4 flex justify-center">
                    <Button size="lg" className="w-full md:w-auto px-8" onClick={() => onSubmit && onSubmit({})}>
                        Submit Form
                    </Button>
                </div>
            </CardContent>
        </Card>
        <div className="text-center mt-6 text-xs text-muted-foreground">
            Powered by PyBase
        </div>
    </div>
  );
};
