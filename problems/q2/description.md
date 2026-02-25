## Objective
Your task is to **integrate** a new global search (Typeahead) component into the internal Enterprise Dashboard. Recruiters use this tool to quickly find candidate profiles across the organization.

## The Challenge
The dashboard's navbar is currently empty. You need to build a responsive search input that fetches users from our mock identity service as the recruiter types, ensuring high performance through **debouncing**.

## Requirements
1.  **Develop the Component**: Complete `Typeahead.tsx` to handle user input.
    - Fetch results from `mockFetchUsers(query)`.
    - Only fetch if the query is **2 or more characters**.
    - Display a **"Loading..."** state while the API call is pending.
    - Display **"No results found"** if the API returns an empty list.
2.  **Debouncing**: Implement a **300ms debounce** to prevent flooding the identity service with requests on every keystroke.
3.  **Global Integration**: Place your finished `Typeahead` component into the `Navbar.tsx` so it is accessible from every page in the dashboard.

## Task Breakdown
1.  **Phase 1**: Implement the debounced fetch logic in `Typeahead.tsx`.
2.  **Phase 2**: Mount the component in `Navbar.tsx` and verify the layout.
3.  **Phase 3**: Verify that clicking a result (optional) or interacting with the list behaves predictably.

## Hints
- You can use the provided `mockFetchUsers` which returns a `Promise<string[]>`.
- The `useEffect` hook with a `setTimeout` cleanup is a standard way to implement debouncing in React.
