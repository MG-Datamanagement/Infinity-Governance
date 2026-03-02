import React from "react";
import { FiDatabase } from "react-icons/fi";
import { IoGlobeOutline } from "react-icons/io5";
import { BsStars } from "react-icons/bs";
import { FiFileText } from "react-icons/fi";
import { RiRobot2Line } from "react-icons/ri";
import { GiScreenImpact } from "react-icons/gi";

interface WelcomeScreenProps {
  onPromptClick: (prompt: string) => void;
}

const SUGGESTED_PROMPTS = [
  {
    icon: FiDatabase,
    title: "List Snowflake Assets",
    description:
      "List all assets in the Snowflake platform related to finance.",
    prompt: "List all assets in the Snowflake platform related to finance.",
  },
  {
    icon: IoGlobeOutline,
    title: "Domain Overview",
    description:
      'Give me an overview of the "Customer 360" domain and its critical assets.',
    prompt:
      'Give me an overview of the "Customer 360" domain and its critical assets.',
  },
  {
    icon: FiFileText,
    title: "Policy Check",
    description:
      "Which datasets are currently violating the GDPR retention policy?",
    prompt: "Which datasets are currently violating the GDPR retention policy?",
  },
  {
    icon: GiScreenImpact,
    title: "Impact Analysis",
    description:
      'What would be the downstream impact if I deprecate the "orders_master" table?',
    prompt:
      'What would be the downstream impact if I deprecate the "orders_master" table?',
  },
];

export const WelcomeScreen: React.FC<WelcomeScreenProps> = ({
  onPromptClick,
}) => {
  return (
    <div className="mx-auto text-center space-y-3">
      <div className="p-2 rounded-lg bg-indigo-200 w-16 h-w-16 flex items-center justify-center mx-auto">
        <RiRobot2Line size={35} className="text-indigo-700" />
      </div>
      <h1 className="text-xl font-bold text-gray-900">
        Welcome to Ask Me Anything!
      </h1>
      <p className="text-sm text-gray-600 leading-relaxed">
        Ask about datasets, lineage, quality, ownership, usage, and
        <br />
        governance to get quick, context-aware insights.
      </p>

      <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-2 gap-4">
        {SUGGESTED_PROMPTS.map((prompt, idx) => {
          const Icon = prompt?.icon;

          return (
            <button
              key={idx}
              className="bg-white border border-gray-300 rounded-xl px-2 py-1 text-left hover:border-indigo-600 hover:shadow-sm transition-all"
              onClick={() => onPromptClick(prompt.prompt)}
            >
              <div className="flex items-center gap-2 space-y-1">
                <Icon className="text-base text-indigo-600" />
                <div className="text-sm font-medium text-gray-900">
                  {prompt.title}
                </div>
              </div>
              <div className="text-center text-xs/5 text-gray-600 leading-relaxed">
                {prompt.description}
              </div>
            </button>
          );
        })}
      </div>
    </div>
  );
};
