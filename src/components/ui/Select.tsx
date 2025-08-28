import React from 'react';

interface SelectProps extends React.SelectHTMLAttributes<HTMLSelectElement> {
  multiple?: boolean;
}

export default function Select(props: SelectProps) {
  return (
    <select {...props} className={`rounded-md border border-gray-300 px-3 py-2 text-sm ${props.className || ''}`.trim()}>
      {props.children}
    </select>
  );
}
