import React from 'react';

// Placeholder UI components to allow build to pass
// Replace with actual shadcn/ui or fumadocs-ui components

export const Tabs = ({ children, className, value, onValueChange }) => (
  <div className={`tabs ${className}`} data-value={value} onChange={onValueChange}>
    {children}
  </div>
);

export const TabsContent = ({ children, className, value }) => (
  <div className={`tabs-content ${className}`} data-value={value}>
    {children}
  </div>
);

export const TabsList = ({ children, className }) => (
  <div className={`tabs-list ${className}`}>
    {children}
  </div>
);

export const TabsTrigger = ({ children, className, value }) => (
  <button className={`tabs-trigger ${className}`} data-value={value}>
    {children}
  </button>
);

export const Accordion = ({ children, className, type }) => (
  <div className={`accordion ${className}`} data-type={type}>
    {children}
  </div>
);

export const AccordionContent = ({ children, className }) => (
  <div className={`accordion-content ${className}`}>
    {children}
  </div>
);

export const AccordionItem = ({ children, className, value }) => (
  <div className={`accordion-item ${className}`} data-value={value}>
    {children}
  </div>
);

export const AccordionTrigger = ({ children, className }) => (
  <button className={`accordion-trigger ${className}`}>
    {children}
  </button>
);

export const Badge = ({ children, className, variant }) => (
  <span className={`badge ${variant} ${className}`}>
    {children}
  </span>
);

export const Card = ({ children, className }) => (
  <div className={`card ${className}`}>
    {children}
  </div>
);

export const CardContent = ({ children, className }) => (
  <div className={`card-content ${className}`}>
    {children}
  </div>
);

export const CardHeader = ({ children, className }) => (
  <div className={`card-header ${className}`}>
    {children}
  </div>
);

export const CardTitle = ({ children, className }) => (
  <h3 className={`card-title ${className}`}>
    {children}
  </h3>
);

export const Select = ({ children, className, value, onValueChange }) => (
  <select className={`select ${className}`} value={value} onChange={(e) => onValueChange(e.target.value)}>
    {children}
  </select>
);

export const SelectContent = ({ children, className }) => (
  <div className={`select-content ${className}`}>
    {children}
  </div>
);

export const SelectItem = ({ children, className, value }) => (
  <option className={`select-item ${className}`} value={value}>
    {children}
  </option>
);

export const SelectTrigger = ({ children, className }) => (
  <div className={`select-trigger ${className}`}>
    {children}
  </div>
);

export const SelectValue = ({ placeholder }) => (
  <span className="select-value">{placeholder}</span>
);

export const Table = ({ children, className }) => (
  <table className={`table ${className}`}>
    {children}
  </table>
);

export const TableBody = ({ children, className }) => (
  <tbody className={`table-body ${className}`}>
    {children}
  </tbody>
);

export const TableCell = ({ children, className }) => (
  <td className={`table-cell ${className}`}>
    {children}
  </td>
);

export const TableHead = ({ children, className }) => (
  <th className={`table-head ${className}`}>
    {children}
  </th>
);

export const TableHeader = ({ children, className }) => (
  <thead className={`table-header ${className}`}>
    {children}
  </thead>
);

export const TableRow = ({ children, className }) => (
  <tr className={`table-row ${className}`}>
    {children}
  </tr>
);

export const Tooltip = ({ children, className }) => (
  <div className={`tooltip ${className}`}>
    {children}
  </div>
);

export const TooltipContent = ({ children, className }) => (
  <div className={`tooltip-content ${className}`}>
    {children}
  </div>
);

export const TooltipTrigger = ({ children, className, asChild }) => {
  const Component = asChild ? React.Fragment : 'button';
  return (
    <Component className={`tooltip-trigger ${className}`}>
      {children}
    </Component>
  );
};

export const Button = ({ children, className, variant, size, onClick }) => (
  <button className={`button ${variant} ${size} ${className}`} onClick={onClick}>
    {children}
  </button>
);