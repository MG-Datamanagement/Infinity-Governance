import React from "react";

interface ConnectorIconProps {
    icon: string;
    className?: string;
}

const ConnectorIcon: React.FC<ConnectorIconProps> = ({
                                                         icon,
                                                         className = "w-9 h-9",
                                                     }) => {
    const icons: Record<string, React.ReactNode> = {
        airflow: (
            <svg viewBox="0 0 40 40" fill="none" className={className}>
                <polygon points="20,4 36,32 4,32" fill="#E8602C" />
            </svg>
        ),
        athena: (
            <svg viewBox="0 0 40 40" fill="none" className={className}>
                <circle cx="20" cy="20" r="14" fill="#9333EA" />
            </svg>
        ),
        azure: (
            <svg viewBox="0 0 40 40" fill="none" className={className}>
                <polygon points="20,4 36,20 20,36 4,20" fill="#0078D4" />
            </svg>
        ),
        bigquery: (
            <svg viewBox="0 0 40 40" fill="none" className={className}>
                <circle cx="20" cy="20" r="14" fill="#4285F4" />
            </svg>
        ),
        cassandra: (
            <svg viewBox="0 0 40 40" fill="none" className={className}>
                <circle cx="20" cy="20" r="14" fill="none" stroke="#E44C2B" strokeWidth="2" />
                <circle cx="20" cy="20" r="7" fill="#E44C2B" />
                <circle cx="20" cy="20" r="3" fill="white" />
            </svg>
        ),
        clickhouse: (
            <svg viewBox="0 0 40 40" fill="none" className={className}>
                <rect x="4" y="8" width="6" height="24" fill="#FACC15" rx="1" />
                <rect x="13" y="8" width="6" height="24" fill="#F59E0B" rx="1" />
                <rect x="22" y="8" width="6" height="24" fill="#EF4444" rx="1" />
                <rect x="31" y="14" width="5" height="12" fill="#3B82F6" rx="1" />
            </svg>
        ),
        cockroach: (
            <svg viewBox="0 0 40 40" fill="none" className={className}>
                <rect x="10" y="4" width="20" height="32" rx="2" stroke="#6B7280" strokeWidth="2" fill="none" />
            </svg>
        ),
        csv: (
            <svg viewBox="0 0 40 40" fill="none" className={className}>
                <path d="M8 4h16l8 8v24H8V4z" stroke="#4B5563" strokeWidth="2" fill="none" />
                <path d="M24 4v8h8" stroke="#4B5563" strokeWidth="2" fill="none" />
                <line x1="13" y1="20" x2="27" y2="20" stroke="#9CA3AF" strokeWidth="1.5" />
                <line x1="13" y1="26" x2="27" y2="26" stroke="#9CA3AF" strokeWidth="1.5" />
            </svg>
        ),
        dagster: (
            <svg viewBox="0 0 40 40" fill="none" className={className}>
                <circle cx="20" cy="20" r="14" stroke="#7C3AED" strokeWidth="2" fill="none" />
                <circle cx="20" cy="20" r="6" stroke="#7C3AED" strokeWidth="2" fill="none" />
                <line x1="20" y1="6" x2="20" y2="14" stroke="#7C3AED" strokeWidth="2" />
                <line x1="20" y1="26" x2="20" y2="34" stroke="#7C3AED" strokeWidth="2" />
                <line x1="6" y1="20" x2="14" y2="20" stroke="#7C3AED" strokeWidth="2" />
                <line x1="26" y1="20" x2="34" y2="20" stroke="#7C3AED" strokeWidth="2" />
            </svg>
        ),
        databricks: (
            <svg viewBox="0 0 40 40" fill="none" className={className}>
                <rect x="4" y="14" width="12" height="12" rx="2" fill="#E8602C" />
                <rect x="20" y="8" width="12" height="12" rx="2" fill="#E8602C" opacity="0.7" />
                <rect x="20" y="22" width="12" height="10" rx="2" fill="#E8602C" opacity="0.4" />
            </svg>
        ),
        dbt: (
            <svg viewBox="0 0 40 40" fill="none" className={className}>
                <polygon points="20,4 36,32 4,32" fill="#E44C2B" />
            </svg>
        ),
        elasticsearch: (
            <svg viewBox="0 0 40 40" fill="none" className={className}>
                <circle cx="20" cy="20" r="14" fill="none" stroke="#0D9488" strokeWidth="2" />
                <circle cx="20" cy="20" r="6" fill="#0D9488" />
                <circle cx="20" cy="20" r="2.5" fill="white" />
            </svg>
        ),
        kafka: (
            <svg viewBox="0 0 40 40" fill="none" className={className}>
                <rect x="5" y="5" width="10" height="30" rx="1" stroke="#6B7280" strokeWidth="1.5" fill="none" />
                <line x1="10" y1="9" x2="10" y2="11" stroke="#6B7280" strokeWidth="1.5" />
                <line x1="10" y1="15" x2="10" y2="17" stroke="#6B7280" strokeWidth="1.5" />
                <line x1="10" y1="21" x2="10" y2="23" stroke="#6B7280" strokeWidth="1.5" />
                <line x1="15" y1="13" x2="24" y2="13" stroke="#6B7280" strokeWidth="1.5" />
                <line x1="15" y1="21" x2="24" y2="21" stroke="#6B7280" strokeWidth="1.5" />
                <rect x="24" y="9" width="11" height="8" rx="1" stroke="#6B7280" strokeWidth="1.5" fill="none" />
                <rect x="24" y="23" width="11" height="8" rx="1" stroke="#6B7280" strokeWidth="1.5" fill="none" />
            </svg>
        ),
        mongodb: (
            <svg viewBox="0 0 40 40" fill="none" className={className}>
                <path d="M20 4 C20 4 10 14 10 22 C10 27.5 14.5 32 20 32 C25.5 32 30 27.5 30 22 C30 14 20 4 20 4Z" fill="#4CAF50" />
                <line x1="20" y1="4" x2="20" y2="32" stroke="#2E7D32" strokeWidth="1.5" />
            </svg>
        ),
        mysql: (
            <svg viewBox="0 0 40 40" fill="none" className={className}>
                <path d="M8 28 C8 28 6 16 20 8 C34 16 32 28 32 28" stroke="#0288D1" strokeWidth="2.5" fill="none" strokeLinecap="round" />
                <path d="M12 28 C16 22 24 22 28 28" stroke="#0288D1" strokeWidth="2.5" fill="none" strokeLinecap="round" />
            </svg>
        ),
        postgresql: (
            <svg viewBox="0 0 40 40" fill="none" className={className}>
                <ellipse cx="20" cy="13" rx="12" ry="9" stroke="#4B5563" strokeWidth="2" fill="none" />
                <path d="M8 13 L8 30 C8 35 32 35 32 30 L32 13" stroke="#4B5563" strokeWidth="2" fill="none" />
                <line x1="14" y1="13" x2="14" y2="34" stroke="#9CA3AF" strokeWidth="1" />
                <line x1="20" y1="22" x2="20" y2="36" stroke="#9CA3AF" strokeWidth="1" />
            </svg>
        ),
        redshift: (
            <svg viewBox="0 0 40 40" fill="none" className={className}>
                <circle cx="20" cy="20" r="14" fill="#EF4444" />
            </svg>
        ),
        snowflake: (
            <svg viewBox="0 0 40 40" fill="none" className={className}>
                <line x1="20" y1="4" x2="20" y2="36" stroke="#0EA5E9" strokeWidth="2" strokeLinecap="round" />
                <line x1="4" y1="20" x2="36" y2="20" stroke="#0EA5E9" strokeWidth="2" strokeLinecap="round" />
                <line x1="7.5" y1="7.5" x2="32.5" y2="32.5" stroke="#0EA5E9" strokeWidth="2" strokeLinecap="round" />
                <line x1="32.5" y1="7.5" x2="7.5" y2="32.5" stroke="#0EA5E9" strokeWidth="2" strokeLinecap="round" />
                <circle cx="20" cy="20" r="4" fill="#0EA5E9" />
            </svg>
        ),
    };

    return <>{icons[icon] ?? null}</>;
};

export default ConnectorIcon;