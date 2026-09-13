/**
 * A small hand-drawn icon set. No icon library: 20 line icons at a consistent
 * 1.6px stroke is less weight and more control than a dependency.
 */
import React from 'react';

const Base = ({ children, size = 18, className = '', ...rest }) => (
  <svg
    width={size}
    height={size}
    viewBox="0 0 24 24"
    fill="none"
    stroke="currentColor"
    strokeWidth="1.6"
    strokeLinecap="round"
    strokeLinejoin="round"
    aria-hidden="true"
    focusable="false"
    className={className}
    {...rest}
  >
    {children}
  </svg>
);

export const IconGauge = (p) => (
  <Base {...p}><path d="M12 14a2 2 0 1 0 0-4 2 2 0 0 0 0 4Z" /><path d="m13.4 10.6 3.6-3.6" /><path d="M20.5 15a9 9 0 1 0-17 0" /></Base>
);
export const IconFootprint = (p) => (
  <Base {...p}><path d="M4 20h16" /><path d="M6 20V9l6-4 6 4v11" /><path d="M10 20v-5h4v5" /></Base>
);
export const IconLeak = (p) => (
  <Base {...p}><path d="M12 3v6" /><path d="M12 22a5 5 0 0 0 5-5c0-3-5-8-5-8s-5 5-5 8a5 5 0 0 0 5 5Z" /></Base>
);
export const IconLoop = (p) => (
  <Base {...p}><path d="M21 12a9 9 0 1 1-3.3-6.9" /><path d="M21 4v5h-5" /></Base>
);
export const IconStudio = (p) => (
  <Base {...p}><path d="M4 20V8" /><path d="M10 20V4" /><path d="M16 20v-8" /><path d="M22 20H2" /></Base>
);
export const IconFlask = (p) => (
  <Base {...p}><path d="M9 3h6" /><path d="M10 3v6.5L5.5 18A2 2 0 0 0 7.3 21h9.4a2 2 0 0 0 1.8-3L14 9.5V3" /><path d="M7.5 15h9" /></Base>
);
export const IconTwin = (p) => (
  <Base {...p}><circle cx="6" cy="6" r="2.4" /><circle cx="18" cy="6" r="2.4" /><circle cx="12" cy="18" r="2.4" /><path d="M7.6 7.8 11 15.7" /><path d="M16.4 7.8 13 15.7" /><path d="M8.4 6h7.2" /></Base>
);
export const IconChecklist = (p) => (
  <Base {...p}><path d="M9 6h11" /><path d="M9 12h11" /><path d="M9 18h11" /><path d="m4 6 1 1 2-2" /><path d="m4 12 1 1 2-2" /><path d="m4 18 1 1 2-2" /></Base>
);
export const IconShield = (p) => (
  <Base {...p}><path d="M12 22s8-3.6 8-10V5.5L12 2 4 5.5V12c0 6.4 8 10 8 10Z" /><path d="m9 12 2 2 4-4" /></Base>
);
export const IconSpark = (p) => (
  <Base {...p}><path d="M12 3v3" /><path d="M12 18v3" /><path d="M3 12h3" /><path d="M18 12h3" /><path d="m5.6 5.6 2.1 2.1" /><path d="m16.3 16.3 2.1 2.1" /><path d="m18.4 5.6-2.1 2.1" /><path d="m7.7 16.3-2.1 2.1" /><circle cx="12" cy="12" r="3" /></Base>
);
export const IconReport = (p) => (
  <Base {...p}><path d="M14 3H7a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2V8Z" /><path d="M14 3v5h5" /><path d="M9 13h6" /><path d="M9 17h4" /></Base>
);
export const IconSettings = (p) => (
  <Base {...p}><circle cx="12" cy="12" r="3" /><path d="M19.4 15a1.7 1.7 0 0 0 .3 1.9l.1.1a2 2 0 1 1-2.8 2.8l-.1-.1a1.7 1.7 0 0 0-2.9 1.2V21a2 2 0 1 1-4 0v-.1A1.7 1.7 0 0 0 7 19.4a1.7 1.7 0 0 0-1.9.3l-.1.1a2 2 0 1 1-2.8-2.8l.1-.1A1.7 1.7 0 0 0 3 15a1.7 1.7 0 0 0-1.6-1H1a2 2 0 1 1 0-4h.1A1.7 1.7 0 0 0 3 9a1.7 1.7 0 0 0-.3-1.9l-.1-.1a2 2 0 1 1 2.8-2.8l.1.1A1.7 1.7 0 0 0 9 3V3a2 2 0 1 1 4 0v.1A1.7 1.7 0 0 0 15 4.6a1.7 1.7 0 0 0 1.9-.3l.1-.1a2 2 0 1 1 2.8 2.8l-.1.1A1.7 1.7 0 0 0 21 9h.1a2 2 0 1 1 0 4H21a1.7 1.7 0 0 0-1.6 1Z" /></Base>
);
export const IconBell = (p) => (
  <Base {...p}><path d="M18 8a6 6 0 1 0-12 0c0 7-3 9-3 9h18s-3-2-3-9" /><path d="M13.7 21a2 2 0 0 1-3.4 0" /></Base>
);
export const IconChevron = (p) => (<Base {...p}><path d="m9 18 6-6-6-6" /></Base>);
export const IconChevronDown = (p) => (<Base {...p}><path d="m6 9 6 6 6-6" /></Base>);
export const IconClose = (p) => (<Base {...p}><path d="M18 6 6 18" /><path d="m6 6 12 12" /></Base>);
export const IconCheck = (p) => (<Base {...p}><path d="m20 6-11 11-5-5" /></Base>);
export const IconAlert = (p) => (
  <Base {...p}><path d="M12 9v4" /><path d="M12 17h.01" /><path d="M10.3 3.9 1.8 18a2 2 0 0 0 1.7 3h17a2 2 0 0 0 1.7-3L13.7 3.9a2 2 0 0 0-3.4 0Z" /></Base>
);
export const IconInfo = (p) => (
  <Base {...p}><circle cx="12" cy="12" r="9" /><path d="M12 16v-4" /><path d="M12 8h.01" /></Base>
);
export const IconSun = (p) => (
  <Base {...p}><circle cx="12" cy="12" r="4" /><path d="M12 2v2" /><path d="M12 20v2" /><path d="m4.9 4.9 1.4 1.4" /><path d="m17.7 17.7 1.4 1.4" /><path d="M2 12h2" /><path d="M20 12h2" /><path d="m6.3 17.7-1.4 1.4" /><path d="m19.1 4.9-1.4 1.4" /></Base>
);
export const IconMoon = (p) => (<Base {...p}><path d="M21 12.8A9 9 0 1 1 11.2 3a7 7 0 0 0 9.8 9.8Z" /></Base>);
export const IconUpload = (p) => (
  <Base {...p}><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" /><path d="m7 9 5-5 5 5" /><path d="M12 4v12" /></Base>
);
export const IconSend = (p) => (<Base {...p}><path d="m22 2-7 20-4-9-9-4Z" /><path d="M22 2 11 13" /></Base>);
export const IconFactory = (p) => (
  <Base {...p}><path d="M2 21h20" /><path d="M4 21V10l5 3V10l5 3V7l5 3v11" /><path d="M7 21v-4" /><path d="M12 21v-4" /><path d="M17 21v-4" /></Base>
);
export const IconMenu = (p) => (<Base {...p}><path d="M3 6h18" /><path d="M3 12h18" /><path d="M3 18h18" /></Base>);
export const IconSearch = (p) => (<Base {...p}><circle cx="11" cy="11" r="7" /><path d="m20 20-3.5-3.5" /></Base>);
export const IconDownload = (p) => (
  <Base {...p}><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" /><path d="m7 10 5 5 5-5" /><path d="M12 15V3" /></Base>
);
export const IconArrowRight = (p) => (<Base {...p}><path d="M5 12h14" /><path d="m12 5 7 7-7 7" /></Base>);
export const IconArrowDown = (p) => (<Base {...p}><path d="M12 5v14" /><path d="m5 12 7 7 7-7" /></Base>);
