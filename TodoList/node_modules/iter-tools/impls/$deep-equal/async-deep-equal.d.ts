declare function asyncDeepEqual(...values: Array<any>): Promise<boolean>;
declare function __asyncDeepEqual(iterables: Array<any>, same?: (a: any, b: any, depth: number) => boolean, coerceNil?: boolean): Promise<boolean>;
export { __asyncDeepEqual, asyncDeepEqual };