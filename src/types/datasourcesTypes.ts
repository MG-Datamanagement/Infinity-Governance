export type ClassifyScanPhase = "never" | "scanning" | "complete" | "re-scan";

export interface DataSourceConfig {
  //   Config - step-1
  uri: string;
  username: string;
  password: string;
  aws_region: string;
  work_group: string;
  s3_staging_dir: string;
  schemaInference: boolean;
  randomSampling: boolean;
  maxSchemaSize: string;
  yamlMode: boolean;
  // Finish - step-4
  name: string;
  piiEnabled: boolean;
  piiApproval: boolean;
  failureEmail: string;
  owner_id: string;
}
