import React from "react";
import ConnectorIcon from "./ConnectorIcon";
import {Connector} from "@/services/mock";

interface ConnectorCardProps {
    connector: Connector;
    onClick?: (connector: Connector) => void;
}

const ConnectorCard: React.FC<ConnectorCardProps> = ({ connector, onClick }) => {
    return (
        <div
            onClick={() => onClick?.(connector)}
            className={`
        ${connector.bgColor} border ${connector.borderColor}
        rounded-2xl p-6 cursor-pointer
        transition-all duration-200 ease-out
        hover:-translate-y-0.5 hover:shadow-lg hover:shadow-black/5
        group
      `}
        >
            <div className="mb-4">
                <ConnectorIcon icon={connector.icon} className="w-9 h-9" />
            </div>
            <h3 className="font-semibold text-gray-800 mb-1 text-[15px] group-hover:text-indigo-600 transition-colors">
                {connector.name}
            </h3>
            <p className="text-gray-500 text-xs leading-relaxed">
                {connector.description}
            </p>
        </div>
    );
};

export default ConnectorCard;